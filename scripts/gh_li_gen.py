#!/usr/bin/env python3
"""
gh_li_gen.py — GitHub-first AMD JSON generator.
Find GitHub users (Indonesia) whose profile lists a LinkedIn URL.
Output: Profile 1 = GitHub, Profile 2 = LinkedIn.

Pipeline: GitHub Search API → dedup against sent → concurrent profile fetch
(name + LinkedIn URL, retry/backoff) → auto-write tracker → AMD JSON.

Optional: set GITHUB_TOKEN env to raise search rate-limit (5000/h vs 60/h).
Token is READ at runtime from env only — never saved, never pushed.
Mode auto: if GITHUB_TOKEN set/unset the script adapts. READ SKILL.md "GITHUB_TOKEN Mode" before exposing.
Scopes needed (fine-grained): Read access to user profile. Write/full-repo token NOT allowed.
"""
import sys, os, json, random, re, time, requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SKILL_DIR = Path.home() / ".hermes/skills/social-media/linkedin-open-to-work/scripts"
sys.path.insert(0, str(SKILL_DIR))
from gen_fresh_li import (amd_json, load_sent, load_addresses, pick_university,
                          normalise_url, split_name, extract_name_from_slug, update_sent)

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0'}
TOKEN = os.environ.get('GITHUB_TOKEN', '').strip()
N_TARGET = 10
OUT = Path("/tmp/gh10_fresh")  # module-level so tests can redirect

def gh_search(query, per_page=15, retries=3):
    """GitHub search API — returns [{login, html_url}]. Retry/backoff on 403/5xx."""
    params = {'q': query, 'per_page': per_page, 'sort': 'followers'}
    headers = {'Accept': 'application/vnd.github+json', **UA}
    if TOKEN: headers['Authorization'] = f'token {TOKEN}'
    for attempt in range(retries):
        try:
            r = requests.get('https://api.github.com/search/users',
                             params=params, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.json().get('items', [])
            if r.status_code in (403, 429):
                # rate-limited — backoff, or give up if no token to retry on
                wait = 2 * (attempt + 1)
                print(f"  [GH search] {r.status_code} {r.text[:60]} → retry in {wait}s")
                time.sleep(wait); continue
            print(f"  [GH search] HTTP {r.status_code}: {r.text[:120]}")
            return []
        except requests.RequestException as e:
            print(f"  [GH search] err {e} → retry {attempt+1}")
            time.sleep(2 * (attempt + 1))
    return []

def profile_extract(login):
    """Fetch GitHub profile HTML → (display_name, linkedin_url)."""
    s = requests.Session(); s.headers.update(UA)
    for attempt in range(3):
        r = s.get(f'https://github.com/{login}', timeout=12)
        if r.status_code == 200:
            break
        if r.status_code in (403, 429): time.sleep(2 * (attempt + 1)); continue
        return None, None
    else:
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
    li = None
    for pat in (r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_%-]+',
                r'(?<![\w:])linkedin\.com/in/[a-zA-Z0-9_%-]+'):
        m = re.search(pat, r.text)
        if m:
            li = m.group(0)
            if not li.startswith('http'): li = 'https://' + li
            break
    if li:
        li = normalise_url(li).rstrip('/')
    return name, li

def build_email(first, last, domains, used):
    """Unused-emails pool per batch to avoid collisions."""
    base = (first + last).lower().replace(' ', '').replace('-', '')
    for _ in range(50):
        e = f"{base}{random.randint(10,99)}@{random.choice(domains)}"
        if e not in used:
            used.add(e); return e
    # ultra-reuse: append more digits
    e = f"{base}{random.randint(1000,9999)}@{random.choice(domains)}"
    used.add(e); return e

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
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.json"): f.unlink()

    seen_gh = set(); seen_li = set(); used_email = set(); gpu_i = 0; done = 0

    for qi, q in enumerate(queries):
        hits = gh_search(q)
        print(f"[{qi+1}/{len(queries)}] {q} → {len(hits)} hits")
        # filter to unscraped candidates (GH url NOT in sent)
        cands = []
        for u in hits:
            gh_url = f'https://github.com/{u["login"]}'
            if u['login'] and u['login'] not in seen_gh and gh_url not in sent:
                seen_gh.add(u['login']); cands.append(u)
        # concurrent profile fetch
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(profile_extract, u['login']): u['login'] for u in cands}
            for fut in as_completed(futs):
                login = futs[fut]
                try: name, li = fut.result()
                except Exception: continue
                if not li or li in sent or li in seen_li:
                    print(f"  {login}: no/dup LinkedIn → skip")
                    continue
                seen_li.add(li)
                if not name:
                    name = extract_name_from_slug(login)
                first, last = split_name(name)
                if first.lower() == last.lower() or len(first) < 2 or len(last) < 2:
                    first, last = split_name(login)
                if first.lower() == last.lower() or len(first) < 2 or len(last) < 2:
                    print(f"  {login}: bad name → skip"); continue

                addr = random.choice(ADDRS)
                city, prov, zipcode = addr[2], addr[3], addr[4]
                univ = pick_university(city) or "Universitas Indonesia"
                phone = f"08{random.randint(11,99)}{random.randint(10000000,99999999)}"
                email = build_email(first, last, DOMAINS, used_email)
                gpu = gpu_cases[gpu_i % len(gpu_cases)]; gpu_i += 1

                data = amd_json(first, last, email, 'amd', f'https://github.com/{login}',
                                (addr[0], addr[1]), city, prov, zipcode, phone, univ, gpu)
                s3 = [s for s in data['profiles'][0]['steps'] if 'Langkah 3' in s['name']][0]
                for fld in s3['fields']:
                    if fld.get('label') == 'Profile 1':
                        fld['key'] = 'profile1'; fld['type'] = 'url'
                s3['fields'].append({'key': 'profile2', 'label': 'Profile 2',
                                     'value': li, 'type': 'url'})
                data['profiles'][0]['github'] = f'https://github.com/{login}'
                data['profiles'][0]['linkedin'] = li
                json.dump(data, open(OUT / f"amd-{login}.json", 'w'), indent=2, ensure_ascii=False)
                # auto-write tracker (dedup: LinkedIn URL + name)
                update_sent(li, f"{first} {last}")
                print(f"  {login} | {first} {last} → {li}")
                done += 1
                if done >= N_TARGET: break
        if done >= N_TARGET: break

    print(f"\nWrote {len(list(OUT.glob('*.json')))} JSON → {OUT}")

if __name__ == '__main__':
    main()