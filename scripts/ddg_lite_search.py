#!/usr/bin/env python3
"""
DDG Lite CDP search for LinkedIn profiles — bypasses search engine blocks from AWS IP.

Usage:
  1. Start Chrome on port 9224:
       CHROME="/home/ubuntu/.cloakbrowser/chromium-146.0.7680.177.5/chrome"
       LD_PRELOAD=/home/ubuntu/fix_chrome_crashpad.so $CHROME \\
         --remote-debugging-port=9224 --remote-allow-origins=* \\
         --user-data-dir=/tmp/cloak-ddgs-\$(date +%s) \\
         --no-sandbox --disable-gpu --headless=new \\
         --disable-blink-features=AutomationControlled \\
         --window-size=1920,1080

  2. Run: python3 ddg_lite_search.py

  3. Process output: /tmp/ddg_urls.json → AMD JSON pipeline
"""
import json, time, urllib.parse, urllib.request, sys
from pathlib import Path

# Add websocket-client from user site-packages if needed
sys.path.insert(0, '/home/ubuntu/.local/lib/python3.14/site-packages')
import websocket

# Add skill helpers
sys.path.insert(0, str(Path.home() / '.hermes/skills/social-media/linkedin-open-to-work/scripts'))
from gen_fresh_li import normalise_url, slug_from_url, extract_name_from_slug

CDP_PORT = 9224
CDP = f"http://127.0.0.1:{CDP_PORT}"

def new_tab(url):
    """Create tab via PUT /json/new (GET returns 405)."""
    req = urllib.request.Request(
        f"{CDP}/json/new?{urllib.parse.quote(url, safe='')}",
        method='PUT', data=b'')
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  tab fail: {e}")
        return None

def close_tab(tid):
    try:
        urllib.request.urlopen(f"{CDP}/json/close/{tid}", timeout=5)
    except:
        pass

def ws_call(tid, method, params=None):
    """CDP Runtime.evaluate via page WebSocket."""
    tabs = json.loads(urllib.request.urlopen(f"{CDP}/json/list", timeout=5).read())
    ws_url = None
    for t in tabs:
        if t['id'] == tid:
            ws_url = t['webSocketDebuggerUrl']
            break
    if not ws_url:
        return None
    mid = int(time.time() * 1000000) % 10000000
    msg = json.dumps({"id": mid, "method": method, "params": params or {}})
    try:
        ws = websocket.create_connection(ws_url, timeout=20)
        ws.send(msg)
        resp = json.loads(ws.recv())
        ws.close()
        return resp
    except Exception as e:
        return {"error": str(e)}

QUERIES = [
    'site:id.linkedin.com/in "mahasiswa aktif" -SMK -SMA -guru',
    'site:linkedin.com/in "bachelor degree" Indonesia student',
    'site:id.linkedin.com/in "lulusan baru" -SMK -SMA',
    'site:linkedin.com/in "informatics" "universitas" Indonesia',
    'site:id.linkedin.com/in "teknik informatika" "Open to Work"',
    'site:id.linkedin.com/in "S.Kom" -dosen -guru'
]

BAD_KEYWORDS = [
    'depok', 'mahasiswa', 'universitas', 'organisasi', 'perusahaan',
    'company', 'sma', 'smk', 'smp', 'sekolah', 'institut',
    'indonesia', 'poetra', 'bangsawan', 'official', 'resmi',
    'channel', 'halaman', 'belahan', 'soulmate', 'pecinta', 'pencinta'
]

seen_slugs = set()
all_urls = []

for qi, q in enumerate(QUERIES):
    print(f"[Q{qi+1}] {q[:55]}...")
    enc = urllib.parse.quote(q)
    search_url = f"https://lite.duckduckgo.com/lite/?q={enc}"

    tab = new_tab(search_url)
    if not tab or 'id' not in tab:
        continue
    tid = tab['id']
    time.sleep(3)

    # Extract page 1
    r1 = ws_call(tid, "Runtime.evaluate", {
        "expression": """JSON.stringify(
  Array.from(document.querySelectorAll('a.result-link'))
    .map(a => a.href)
    .filter(u => u.includes('linkedin.com/in/'))
)"""})

    # Paginate
    ws_call(tid, "Runtime.evaluate", {
        "expression": """(function(){
  var b=document.querySelector('input.navbutton');
  if(b){b.click();return 1}return 0})()"""})
    time.sleep(3)

    # Extract page 2
    r2 = ws_call(tid, "Runtime.evaluate", {
        "expression": """JSON.stringify(
  Array.from(document.querySelectorAll('a.result-link'))
    .map(a => a.href)
    .filter(u => u.includes('linkedin.com/in/'))
)"""})

    close_tab(tid)

    # Collect raw URLs from both pages
    raw = []
    for r in (r1, r2):
        if r and 'result' in r:
            try:
                raw += json.loads(r['result']['result']['value'])
            except:
                pass

    # Decode DDG redirect URLs
    decoded = []
    for u in raw:
        if 'uddg=' in u:
            du = urllib.parse.unquote(u.split('uddg=')[1].split('&')[0])
            decoded.append(du)
        else:
            decoded.append(u)

    # Filter & dedup
    new = 0
    for u in decoded:
        nu = normalise_url(u)
        slug = slug_from_url(nu)
        if not slug or len(slug) < 5:
            continue
        if any(kw in slug.lower() for kw in BAD_KEYWORDS):
            continue
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            all_urls.append(nu)
            new += 1

    print(f"  {len(decoded)} URLs, {new} new")

print(f"\n=== TOTAL: {len(all_urls)} unique ===")
for u in all_urls:
    slug = slug_from_url(u)
    name = extract_name_from_slug(slug)
    print(f"  {slug}")

json.dump(all_urls, open("/tmp/ddg_urls.json", "w"), indent=2)
print(f"\nSaved to /tmp/ddg_urls.json ({len(all_urls)} URLs)")
print(f"\nNext step: process via gen_fresh_li helpers -> AMD JSON -> ZIP")
