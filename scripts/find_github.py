#!/usr/bin/env python3
"""
find_github.py — find matching GitHub account for a given LinkedIn first/last name.

Strategy (lightest → deepest):
1. Direct guess: github.com/<firstname+lastname>, lastname+firstname, etc.
2. GitHub Search API for exact quoted name.
3. If not found, try Yahoo search site:github.com via CamoFox; score by match density.

Returns best match (score≥2 = one name match, ≥3 = two-part match).

Usage:
    from find_github import find_github_account
    result = find_github_account('Abdul', 'Siregar')
    # → {'slug': 'Adib-F', 'url': 'https://github.com/Adib-F', 'display': 'Muhammad Adib Fakhri Siregar', 'score': 2} 
    # or None if no match
"""
import requests, re, time, urllib.parse, json, subprocess
from pathlib import Path

CAMOFOX_BASE = "http://127.0.0.1:9377"
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0'

def _api_config():
    s = requests.Session()
    s.headers['User-Agent'] = UA
    return s

def _tokens(text):
    return set(re.findall(r'[a-zA-Z]{2,}', (text or '').lower()))

def score_match(slug_or_display, firstname, lastname):
    """Score: 0 = no match, 1 = weak, 2 = one part, 4 = full match."""
    if not slug_or_display: return 0
    lower = slug_or_display.lower()
    fn, ln = firstname.lower(), lastname.lower()
    score = 0
    if fn in lower: score += 2
    if ln in lower: score += 2
    if fn in lower and ln in lower: score = 4
    return score

def try_direct_guesses(s, firstname, lastname):
    """Try github.com/<firstname+lastname>, etc. Returns first 200-hit dict or None."""
    fn_clean = re.sub(r'[^a-z0-9]', '', firstname.lower())
    ln_clean = re.sub(r'[^a-z0-9]', '', lastname.lower())
    variants = [
        fn_clean + ln_clean,
        fn_clean + '-' + ln_clean,
        ln_clean + fn_clean,
        (fn_clean[0] if fn_clean else '') + ln_clean,
        fn_clean + (ln_clean[0] if ln_clean else ''),
    ]
    seen = set()
    for v in variants:
        if not v or v in seen or len(v) < 3: continue
        seen.add(v)
        r = s.get(f'https://api.github.com/users/{v}', timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {'slug': d.get('login'), 'url': d.get('html_url'),
                    'display': d.get('name') or '', 'score': score_match(d.get('name') or v, firstname, lastname)}
    return None

def try_github_search(s, firstname, lastname):
    """GitHub /search/users — exact quoted name."""
    quotes = [f'"{firstname} {lastname}"', f'{firstname} {lastname}', f'{lastname} {firstname}']
    for q in quotes:
        r = s.get('https://api.github.com/search/users',
                  params={'q': q, 'per_page': 3}, timeout=10)
        if r.status_code != 200: continue
        items = r.json().get('items', [])
        for u in items:
            v = s.get(f"https://api.github.com/users/{u.get('login')}", timeout=8)
            if v.status_code != 200: continue
            d = v.json()
            sc = score_match(d.get('name') or u.get('login'), firstname, lastname)
            if sc >= 2:
                return {'slug': d.get('login'), 'url': d.get('html_url'),
                        'display': d.get('name') or '', 'score': sc}
    return None

def _camofox_api(method, path, data=None, timeout=45):
    cmd = ["curl", "-s", "--max-time", str(timeout), "-X", method, CAMOFOX_BASE + path]
    if data: cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
        return json.loads(out.stdout.decode())
    except:
        return {}

def _yahoo_github_candidates(query, session_key):
    """Search Yahoo, extract github.com/<slug> URLs."""
    t = _camofox_api("POST", "/tabs", {"userId": "sugab", "sessionKey": session_key})
    tab = t.get("tabId")
    if not tab: return []
    url = "https://search.yahoo.com/search?p=" + urllib.parse.quote(query) + "&ei=UTF-8"
    _camofox_api("POST", f"/tabs/{tab}/navigate", {"userId": "sugab", "url": url})
    time.sleep(7)
    snap = _camofox_api("GET", f"/tabs/{tab}/snapshot?userId=sugab")
    text = snap.get("snapshot", "")
    slugs = re.findall(r'https?://github\.com/([a-zA-Z0-9_.-]{3,39})(?!/)', text)
    slugs = [s for s in dict.fromkeys(slugs) if re.match(r'^[a-zA-Z0-9]', s)]  # dedup + valid start
    _camofox_api("POST", f"/tabs/{tab}/close?userId=sugab")
    return slugs

def verify_github_profile(s, slug):
    """Fetch profile, extract display name."""
    r = s.get(f'https://github.com/{slug}', timeout=10, allow_redirects=True)
    if r.status_code != 200: return None
    t = re.search(r'<title>([^|<]+)[|<]', r.text)
    title = t.group(1).strip() if t else ''
    m = re.search(r'\(([^)]+)\)', title)
    display = m.group(1).strip() if m else ''
    # fallback: og:title format # slug (Display Name)
    if not display:
        alt = re.search(r'property="og:title" content="([^"]+)"', r.text)
        if alt: display = alt.group(1)
    return {'slug': slug, 'display': display, 'url': f'https://github.com/{slug}'}

def find_github_account(firstname, lastname, camofox=True, min_score=2, verbose=False):
    """
    Find best GitHub account matching name. Returns dict or None.
    Args:
        firstname, lastname: strings from LinkedIn
        camofox: use CamoFox+Yahoo fallback if API fails (slow ~30s, broader coverage)
        min_score: threshold for accepting match (default 2 = one name part)
    """
    s = _api_config()

    def log(*a):
        if verbose: print(*a)

    # Pass 1: Direct guesses
    log(f"[1] direct guesses for {firstname} {lastname}...")
    r = try_direct_guesses(s, firstname, lastname)
    if r and r['score'] >= min_score: return r
    log(f"  → {'hit score ' + str(r['score']) if r else 'none'}")

    # Pass 2: GitHub search API
    log(f"[2] GitHub search API...")
    r = try_github_search(s, firstname, lastname)
    if r and r['score'] >= min_score: return r
    log(f"  → {'hit score ' + str(r['score']) if r else 'none'}")

    # Pass 3: CamoFox Yahoo search site:github.com
    if camofox:
        log(f"[3] CamoFox Yahoo fallback...")
        session = f"gh-{int(time.time())}"
        # Two queries: full name, then last name only
        for qtype, q in [
            ('quoted', f'"{firstname} {lastname}" site:github.com'),
            ('lastonly', f'{lastname} site:github.com'),
        ]:
            log(f"    q={qtype}: {q[:60]}")
            slugs = _yahoo_github_candidates(q, f"{session}-{qtype}")
            log(f"    → {len(slugs)} slugs")
            # Score each by fetching profile
            best = None
            best_score = 0
            for slug in slugs:
                v = verify_github_profile(s, slug)
                if not v: continue
                # also score against slug itself
                combined = f"{v['display']} {v['slug']}"
                v['score'] = score_match(combined, firstname, lastname)
                if v['score'] > best_score:
                    best, best_score = v, v['score']
            if best and best_score >= min_score:
                return best

    return None


if __name__ == '__main__':
    import sys
    fn, ln = sys.argv[1:3] if len(sys.argv) >= 3 else ('Abdul', 'Siregar')
    r = find_github_account(fn, ln, verbose=True)
    print(json.dumps(r, indent=2, ensure_ascii=False))
