# AMD JSON generator + LinkedIn search with optional GitHub attachment
# Combines: li_search.py + li_gen.py + find_github_account
import sys, json, random, re, time, subprocess, urllib.parse
from pathlib import Path

SKILL_DIR = Path.home() / ".hermes/skills/social-media/linkedin-open-to-work/scripts"
sys.path.insert(0, str(SKILL_DIR))
from gen_fresh_li import (normalise_url, slug_from_url, extract_name_from_slug,
    split_name, amd_json, load_sent, load_addresses, pick_university)

CAMOFOX = "http://127.0.0.1:9377"

# ---- GitHub search (Yahoo CamoFox — no API rate limits) ----
def _api(method, path, data=None, timeout=60):
    cmd = ["curl", "-s", "--max-time", str(timeout), "-X", method, CAMOFOX + path]
    if data: cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    out = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
    try: return json.loads(out.stdout.decode())
    except: return {}

NOISE = {'login','search','register','signup','github','orgs','explore','features','pricing','settings','notifications',''}

def find_github_account(firstname, lastname):
    """Search github account matching name. Returns {'slug','url','score'} or None."""
    fn = firstname.strip(); ln = lastname.strip()
    if len(fn) < 2: return None
    fn_l, ln_l = fn.lower(), ln.lower()
    
    t = _api("POST", "/tabs", {"userId": "sugab", "sessionKey": f"gh-{int(time.time()*1000)}"})
    tab = t.get("tabId")
    if not tab: return None
    
    q = f'github.com "{fn} {ln}"'
    _api("POST", f"/tabs/{tab}/navigate", {"userId": "sugab",
        "url": f"https://search.yahoo.com/search?p={urllib.parse.quote(q)}&ei=UTF-8"})
    time.sleep(8)
    # Grab root-level github.com/<slug> links (exclude noise)
    expr = '''Array.from(document.querySelectorAll("a")).filter(a=>{
      const h=a.href;
      if(!h.startsWith("https://github.com/")) return false;
      const parts=h.slice(19).split("/");
      return parts.length===1 && parts[0].length>3;
    }).map(a=>a.href.slice(19)).filter(s=>!["login","search","register","signup","github","orgs","explore","features","pricing","settings","notifications",""].includes(s.toLowerCase())).slice(0,10)'''
    r = _api("POST", f"/tabs/{tab}/evaluate", {"userId": "sugab", "expression": expr})
    _api("POST", f"/tabs/{tab}/close?userId=sugab")
    
    slugs = r.get('result', [])
    if not slugs: return None
    
    def score(slug):
        s = slug.lower()
        sc = 0
        if len(fn_l) >= 3 and fn_l in s: sc += 2
        if len(ln_l) >= 3 and ln_l in s: sc += 2
        if fn_l in s and ln_l in s: sc = 4
        return sc
    
    best, best_sc = None, 0
    for slug in slugs:
        sc = score(slug)
        if sc > best_sc:
            best, best_sc = {'slug': slug, 'url': f'https://github.com/{slug}', 'score': sc}, sc
    return best if best and best_sc >= 2 else None

# ---- LinkedIn search (existing) ----
def search_yahoo_li(query, session_key):
    t = _api("POST", "/tabs", {"userId": "sugab", "sessionKey": session_key})
    tab = t.get("tabId")
    if not tab: return []
    url = "https://search.yahoo.com/search?p=" + urllib.parse.quote(query) + "&ei=UTF-8"
    _api("POST", f"/tabs/{tab}/navigate", {"userId": "sugab", "url": url})
    time.sleep(8)
    snap = _api("GET", f"/tabs/{tab}/snapshot?userId=sugab")
    text = snap.get("snapshot", "")
    links = re.findall(r'https://[a-z]{2,4}\.linkedin\.com/in/[a-zA-Z0-9_%-]+', text)
    links = list(dict.fromkeys(links))
    _api("POST", f"/tabs/{tab}/close?userId=sugab")
    return links

# ---- Main ----
if __name__ == '__main__':
    # SAMPLE: pick 10 fresh LinkedIn profiles (rotate query profession batch)
    QUERIES = [
        'site:id.linkedin.com/in "Open to Work" programmer Jakarta',
        'site:id.linkedin.com/in "Open to Work" developer Bandung',
        'site:id.linkedin.com/in "Open to Work" designer Medan',
        'site:id.linkedin.com/in "Open to Work" engineer Surabaya',
        'site:id.linkedin.com/in "Open to Work" coder Yogyakarta',
        'site:id.linkedin.com/in "Open to Work" IT Tangerang',
        'site:id.linkedin.com/in "Open to Work" software Semarang',
    ]
    
    all_links = []
    for i, q in enumerate(QUERIES):
        print(f"[{i+1}/{len(QUERIES)}] {q[:50]}")
        links = search_yahoo_li(q, f"li-{i}-{int(time.time())}")
        print(f"  → {len(links)}")
        all_links.extend(links)
        time.sleep(2)
    
    urls = sorted(set(all_links))
    print(f"\nTotal: {len(urls)}")
    
    # Dedup & filter
    SENT = load_sent()
    BAD_KW = ['depok','mahasiswa','universitas','organisasi','perusahaan','company',
              'sma','smk','smp','sekolah','institut','official','resmi','channel','halaman',
              'belahan','soulmate','job-seeker','open-to-work','welcome','career','jobs']
    
    profiles, seen = [], set()
    for u in urls:
        nu = normalise_url(u)
        if nu.startswith('https:/') and not nu.startswith('https://'): nu = 'https://' + nu[7:]
        slug = slug_from_url(nu)
        if not slug or slug in seen or slug in SENT or nu in SENT: continue
        low = slug.lower()
        if any(k in low for k in BAD_KW) or len(slug) < 5: continue
        first, last = split_name(extract_name_from_slug(slug))
        if first.lower() == last.lower() or len(first) < 2 or len(last) < 2: continue
        seen.add(slug)
        profiles.append({"url": nu, "slug": slug, "first": first, "last": last})
        if len(profiles) == 10: break
    
    print(f"Selected {len(profiles)}")
    
    # Enrich: GitHub + address, etc.
    ADDRS = load_addresses()
    gpu_data = json.load(open(Path.home() / ".hermes/data/gpu_use_cases.json"))
    gpu_cases = gpu_data["use_cases"] if isinstance(gpu_data, dict) else gpu_data
    random.shuffle(gpu_cases)
    DOMAINS = ["ubsi.biz.id", "gmailedu.web.id", "ikhsanmaul.web.id", "richadbasudara.my.id"]
    OUT = Path("/tmp/li10_fresh")
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.json"): f.unlink()
    
    gpu_i = 0
    for p in profiles:
        addr = random.choice(ADDRS)
        city, prov, zipcode = addr[2], addr[3], addr[4]
        univ = pick_university(city) or "Universitas Indonesia"
        phone = f"08{random.randint(11,99)}{random.randint(10000000,99999999)}"
        domain = random.choice(DOMAINS)
        local = (p['first'] + p['last']).lower().replace(' ', '') + str(random.randint(10,99))
        email = f"{local}@{domain}".replace(' ','')
        gpu = gpu_cases[gpu_i % len(gpu_cases)]; gpu_i += 1
        data = amd_json(p['first'], p['last'], email, domain, p['url'],
                        (addr[0], addr[1]), city, prov, zipcode, phone, univ, gpu)
        
        # NEW: Search GitHub with verification
        gh = find_github_account(p['first'], p['last'])
        if gh and gh['score'] >= 2:
            data['profiles'][0]['github'] = gh['url']
            # also inject into Step 3
            s3 = [s for s in data['profiles'][0]['steps'] if 'Langkah 3' in s['name']][0]
            s3['fields'].append({
                'key': 'githubProfile',
                'label': 'GitHub Profile',
                'value': gh['url'],
                'type': 'text'
            })
            print(f"  {p['first']} {p['last']} → GH: {gh['url']} (score {gh['score']})")
        else:
            print(f"  {p['first']} {p['last']} → no GitHub")
        
        json.dump(data, open(OUT / f"amd-{p['slug'][:30]}.json", 'w'), indent=2, ensure_ascii=False)
        time.sleep(1)  # Rate limit CamoFox
    
    print(f"\nWrote {len(list(OUT.glob('*.json')))} JSON → {OUT}")
