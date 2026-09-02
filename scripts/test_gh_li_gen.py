#!/usr/bin/env python3
"""Self-check for gh_li_gen core build logic (no network).
Monkeypatches profile_extract + gh_search; asserts P1=GitHub, P2=LinkedIn,
uniq emails, dedup-by-LinkedIn. Run: python3 test_gh_li_gen.py"""
import json, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, '/tmp/liotw-repo/scripts')
import importlib
m = importlib.import_module('gh_li_gen')

# --- monkeypatch network fns ---
FAKE = {
    'userone':  ('User One', 'https://www.linkedin.com/in/user-one'),
    'usertwo':  ('User Two', 'https://www.linkedin.com/in/user-two'),
    'dupuser':  ('Dup User', 'https://www.linkedin.com/in/user-one'),  # dup LI of userone
    'noli':     ('No Li', None),
}
def fake_extract(login):
    return FAKE.get(login, (None, None))
def fake_search(q, **kw):
    return [{'login': k} for k in FAKE]
m.profile_extract = fake_extract
m.gh_search = fake_search
m.load_sent = lambda: set()  # empty tracker
m.N_TARGET = 3  # expect userone, usertwo (noli & dup skipped)

# stash real paths: redirect OUT to tmp
tmp = Path(tempfile.mkdtemp())
m.OUT = tmp
m.Path = Path

# capture update_sent calls
written = []
m.update_sent = lambda url, name: written.append((url, name))

m.main()

files = sorted(tmp.glob('*.json'))
assert len(files) == 2, f"expected 2 files, got {[f.name for f in files]}"
lis = []
for f in files:
    d = json.load(open(f))
    s3 = [s for s in d['profiles'][0]['steps'] if 'Langkah 3' in s['name']][0]
    p1 = next(x for x in s3['fields'] if x.get('key') == 'profile1')
    p2 = next(x for x in s3['fields'] if x.get('key') == 'profile2')
    assert p1['value'].startswith('https://github.com/'), p1
    assert p2['value'].startswith('https://www.linkedin.com/in/'), p2
    assert p1['type'] == 'url' and p2['type'] == 'url'
    lis.append(p2['value'])
    # address/city/zip present
    labels = {x.get('label') for s in d['profiles'][0]['steps'] for x in s.get('fields', [])}
    assert 'Address 1' in labels and 'Postal Code' in labels
# LinkedIn URLs unique across the 2 files (dedup worked — only 1 of the 2 same-LI users kept)
assert len(set(lis)) == 2, f"LinkedIn dup not deduped {lis}"
# exactly ONE of dupuser/userone (same LI) survived — dedup by LinkedIn
logins = [f.name.replace('amd-', '').replace('.json', '') for f in files]
same_li = [l for l in logins if l in ('userone', 'dupuser')]
assert len(same_li) == 1, f"expected 1 of userone/dupuser, got {logins}"
assert 'usertwo' in logins, logins

# emails unique across files
emails = [next(x['value'] for s in json.load(open(f))['profiles'][0]['steps'] if 'Langkah 1' in s['name'] for x in s['fields'] if x['label'] == 'E-mail') for f in files]
assert len(set(emails)) == len(emails), f"email collision {emails}"
# tracker wrote exactly 2 (one per produced file)
assert len(written) == 2, written

print("ALL PASS: 2 JSON, P1=GitHub P2=LinkedIn, emails unique, dup-LI skipped, tracker written")
print("files:", [f.name for f in files])