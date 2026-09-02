#!/usr/bin/env python3
"""
gh_li_gen.py — GitHub-first AMD JSON generator.
Find GitHub users (Indonesia) whose profile lists a LinkedIn URL.
Output: Profile 1 = GitHub, Profile 2 = LinkedIn.

Pipeline: GitHub Search API → dedup against sent → fetch profile name + LinkedIn URL → AMD JSON.
"""
import sys, json, random, re, time, requests
from pathlib import Path

SKILL_DIR = Path.home() / ".hermes/skills/social-media/linkedin-open-to-work/scripts"
sys.path.insert(0, str(SKILL_DIR))
from gen_fresh_li import (amd_json, load_sent, load_addresses, pick_university,
                          normalise_url, split_name, extract_name_from_slug)

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0'}
PHONE_SUFFIX = re.compile(r'\d+')

def gh_search(query, per_page=15):
    """GitHub search API — returns [{login, html_url}]."""
    r = requests.get('https://api.github.com/search/users',
                     params={'q': query, 'per_page': per_page, 'sort': 'followers'},
                     headers={'Accept': 'application/vnd.github+json', **UA}, timeout=15)
    if r.status_code != 200:
        print(f"  [GH search] HTTP {r.status_code}: {r.text[:120]}")
        return []
    return r.json().get('items', [])

def profile_extract(login):
    """Fetch GitHub profile HTML → (display_name, linkedin_url) or (None, None)."""
    s = requests.Session(); s.headers.update(UA)
    r = s.get(f'https://github.com/{login}', timeout=12)
    if r.status_code != 200:
        return None, None
    name = None
    m = re.search(r'<title>([^<]+)</title>', r.text)
    if m:
        inner = m.group(1).split('·')[0].strip()
        paren = re.search(r'\(([^)]+)\)', inner)
        name = paren.group(1).strip() if paren else inner.strip('() ')
    if not name or name.lower() == login.lower():
        alt = re.search(r'property="og:title" content="([^"]+)"', r.text)
        if alt: name = alt.group(1).split(' · ')[0].split('(')[0].strip()
    m2 = re.search(r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_%-]+', r.text)
    li = m2.group(0) if m2 else None
    if not li:
        m3 = re.search(r'(?<![:\w])linkedin\.com/in/[a-zA-Z0-9_%-]+', r.text)
        li = ('https://' + m3.group(0)) if m3 else None
    return name, li

def main():
    queries = [
        'linkedin location:Indonesia language:Python',
        'linkedin location:Indonesia language:JavaScript',
        'linkedin location:Indonesia language:Java',
        'linkedin location:Indonesia language:Go',
        'linkedin location:Indonesia language:TypeScript',
        'linkedin location:Indonesia language:PHP',
    ]
    sent = load_sent()
    ADDRS = load_addresses()
    gpu_data = json.load(open(Path.home() / ".hermes/data/gpu_use_cases.json"))
    gpu_cases = gpu_data["use_cases"] if isinstance(gpu_data, dict) else gpu_data
    random.shuffle(gpu_cases)
    DOMAINS = ["ubsi.biz.id", "gmailedu.web.id", "ikhsanmaul.web.id", "richadbasudara.my.id"]
    OUT = Path("/tmp/gh10_fresh"); OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.json"): f.unlink()

    seen_gh = set(); gpu_i = 0; done = 0

    for qi, q in enumerate(queries):
        hits = gh_search(q)
        print(f"[{qi+1}/{len(queries)}] {q} → {len(hits)} hits")
        for u in hits:
            login = u['login']
            if not login or login in seen_gh or f'https://github.com/{login}' in sent:
                continue
            seen_gh.add(login)
            name, li = profile_extract(login)
            if not li:
                print(f"  {login}: no LinkedIn → skip")
                continue
            if not name:
                name = extract_name_from_slug(login)
            first, last = split_name(name)
            if first.lower() == last.lower() or len(first) < 2 or len(last) < 2:
                first, last = split_name(login)
            if first.lower() == last.lower() or len(first) < 2 or len(last) < 2:
                print(f"  {login}: bad name → skip")
                continue

            addr = random.choice(ADDRS)
            city, prov, zipcode = addr[2], addr[3], addr[4]
            univ = pick_university(city) or "Universitas Indonesia"
            phone = f"08{random.randint(11,99)}{random.randint(10000000,99999999)}"
            domain = random.choice(DOMAINS)
            local = (first + last).lower().replace(' ','') + str(random.randint(10,99))
            email = f"{local}@{domain}".replace(' ','')
            gpu = gpu_cases[gpu_i % len(gpu_cases)]; gpu_i += 1

            data = amd_json(first, last, email, domain, f'https://github.com/{login}',
                            (addr[0], addr[1]), city, prov, zipcode, phone, univ, gpu)
            s3 = [s for s in data['profiles'][0]['steps'] if 'Langkah 3' in s['name']][0]
            # P1 = GitHub (key+type for autofill), P2 = LinkedIn
            for fld in s3['fields']:
                if fld.get('label') == 'Profile 1':
                    fld['key'] = 'profile1'; fld['type'] = 'url'
            s3['fields'].append({'key': 'profile2', 'label': 'Profile 2',
                                 'value': li, 'type': 'url'})
            data['profiles'][0]['github'] = f'https://github.com/{login}'
            data['profiles'][0]['linkedin'] = li
            json.dump(data, open(OUT / f"amd-{login}.json", 'w'), indent=2, ensure_ascii=False)
            print(f"  {login} | {first} {last} → LI: {li}")
            done += 1
            if done >= 10: break
            time.sleep(1)  # rate limit GH API
        if done >= 10: break

    print(f"\nWrote {len(list(OUT.glob('*.json')))} JSON → {OUT}")

if __name__ == '__main__':
    main()