#!/usr/bin/env python3
"""
Inline LinkedIn → AMD JSON pipeline (Yahoo curl search + dedup + JSON gen).

Standalone alternative to combo_unique when search engines block AWS IP.
Run from /tmp to avoid polluting the skill directory.

Usage:
    python3 gen_fresh_li.py

Output: /tmp/li10_fresh/li10_fresh_yahoo.zip (10 JSON files + ZIP)
"""
import json, random, pathlib, zipfile, re, subprocess, urllib.parse, sys
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
DOMAINS = ["ubsi.biz.id", "gmailedu.web.id", "ikhsanmaul.web.id", "richadbasudara.my.id"]
PASSWORD = "PasswordKuat!1"
PHONE_PREFIX = "628"
DEFAULT_CITY = "Jakarta"
DEFAULT_PROVINCE = "DKI Jakarta"

# Paths
SKILL_DIR = pathlib.Path.home() / ".hermes/skills/social-media/linkedin-open-to-work"
AMD_DIR = pathlib.Path.home() / ".hermes/skills/social-media/amd-register-sugab"
GPU_CASES = pathlib.Path.home() / ".hermes/data/gpu_use_cases.json"
SENT_LI = SKILL_DIR / "data" / "sent_profiles.json"
SENT_AMD = AMD_DIR / "data" / "sent_amd_profiles.json"
ADDR_FILE = SKILL_DIR / "data" / "address.txt"
CITIES_UNIV = SKILL_DIR / "data" / "cities_univ.json"
CACHE_FILE = SKILL_DIR / "data" / "linkedin_cache.json"
OUT_DIR = pathlib.Path("/tmp/li10_fresh")
N_TARGET = 10

# ─── Helpers ──────────────────────────────────────────────────────────────

def normalise_url(url):
    url = url.rstrip('/').split('?')[0].split('#')[0]
    url = re.sub(r'https://[a-z]{2}\.linkedin\.com/', 'https://linkedin.com/', url)
    url = re.sub(r'https://www\.linkedin\.com/', 'https://linkedin.com/', url)
    url = re.sub(r'/(en|id)$', '', url)
    # Strip Yahoo redirect junk after the slug
    url = re.sub(r'(/in/[a-zA-Z0-9_-]+).*', r'\1', url)
    return url

def slug_from_url(url):
    slug = normalise_url(url).split('/in/')[-1].rstrip('/')
    # Strip Yahoo redirect junk (rk=, rs= query params)
    slug = re.sub(r'[?/].*$', '', slug)
    return slug

# ─── Bad Slug Filter ───────────────────────────────────────────────────────
BAD_KEYWORDS = [
    'depok', 'mahasiswa', 'universitas', 'organisasi', 'perusahaan',
    'company', 'sma', 'smk', 'smp', 'sekolah', 'institut',
    'indonesia', 'poetra', 'putra', 'bangsawan',
    'belahan-jiwa', 'soulmate', 'pecinta', 'pencinta',
    'official', 'resmi', 'channel', 'halaman',
    'bp', 'bapak', 'pak', 'ibu', 'bu',
]

def is_bad_name(name, slug):
    """Check if a name/slug looks like a non-person profile."""
    name_lower = name.lower()
    slug_lower = slug.lower()

    # Check slugs against bad keywords
    if any(kw in slug_lower for kw in BAD_KEYWORDS):
        return True
    if any(kw in name_lower for kw in BAD_KEYWORDS):
        return True

    # Check for non-name patterns
    if len(name.replace(' ', '')) < 4:
        return True
    # Only letters and spaces allowed in clean names
    if not all(c.isalpha() or c.isspace() for c in name.replace('-', '')):
        return True
    # Single-word names that are very long are suspicious
    if ' ' not in name and len(name) > 20:
        return True
    # Check if slug contains non-name words
    for kw in ['belahan', 'sayang', 'cinta', 'kasih', 'manja']:
        if kw in slug_lower:
            return True

    return False

def split_name(name):
    """Split full name into first/last. Never returns empty last_name."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return parts[0].capitalize(), ' '.join(parts[1:]).title()

    # Single word — use multi-strategy split
    word = parts[0]

    # Strategy A: Known Indonesian suffixes (family names / matronymic)
    suffixes = [
        'wati','sari','ning','tresni','sih','yanti','wulan','dewi','hati','putri',
        'ningsih','susanti','cahyani','setyowati','astuti','sutanti',
        'permadi','wijaya','kusuma','pratama','hermawan','setiawan','santoso',
        'haryanto','purnama','rahayu','handayani','kusumo','utami',
        'susilo','hariyadi','maryati','sumarni','setyawan','susanto',
        'alhaq','hanafi','gallaghera','harjani','ardiansyah',
        'permana','hendrawan','wibowo','gunawan','nugroho','prasetyo',
        'fauzi','syahputra','maulana','ramadhan','hidayat','anshori',
        'cholili','drajatun','sitompul',
        'hapsari','kartika','maratus','diyas','nurhayati','syahfitri',
        'kurniawan','kurniati','susilowati','indriani','novitasari',
        'aryani','hamidah','rahmawati','hasanah','afifah','azizah',
        'nadhif','rinaldi','syawal','mustofa','mustika','safitri',
        'agustina','oktaviani','komalasari','selvia',
        'prakoso','tama','anggara','saputra','pranata',
    ]
    wl = word.lower()
    for suf in suffixes:
        if wl.endswith(suf) and len(word) > len(suf) + 2:
            sp = len(word) - len(suf)
            return word[:sp].capitalize(), word[sp:].capitalize()

    # Strategy B: Known Indonesian first-name prefixes
    prefixes = [
        'muhammad','ahmad','abdul','abu','ibnu','siti','raden','tengku','teuku',
        'agus','fikri','fitri','nurul','nur','rizky','rizki','aditya',
        'dwi','tri','eka','andi','rian','rudi','budi','dedi','hendra',
        'ari','aji','bayu','gilang','reza','dimas','rama','tito',
        'fajar','fahrul','faqih','irfan','iqbal','ismail','joko',
        'slamet','sutrisno','supriyadi','surya','wahyu','eko',
        'bambang','sigit','sugeng','suprapto','suwardi',
    ]
    for pref in prefixes:
        if wl.startswith(pref) and len(word) > len(pref) + 2:
            sp = len(pref)
            return word[:sp].capitalize(), word[sp:].capitalize()

    # Strategy C: Split mid-length words at natural boundary
    if len(word) >= 5:
        # Prefer consonant-vowel boundary near 45-50% of word
        mid = len(word) * 45 // 100  # slightly before middle for balanced look
        best = mid
        # Search ±2 around mid for a CV boundary (consonant → vowel)
        for delta in range(-2, 3):
            p = mid + delta
            if 1 < p < len(word) - 1:
                if word[p-1] not in 'aeiouAEIOU' and word[p] in 'aeiouAEIOU':
                    best = p
                    break
                # Vowel-start last part is second best
                if word[p] in 'aeiouAEIOU':
                    best = p
        # Ensure parts aren't same
        if word[:best].lower() == word[best:].lower() and best != 0:
            best = max(2, min(len(word)-2, best + 1))
        return word[:best].capitalize(), word[best:].capitalize()

    # Strategy D: 4-char words — split at position 2
    if len(word) == 4:
        return word[:2].capitalize(), word[2:].capitalize()

    # Last resort: word is too short to split meaningfully — use whole word (never empty)
    return word.capitalize(), word.capitalize()

def load_sent():
    """Load sent tracking from both LI and AMD files."""
    sent = set()
    for f in [SENT_LI, SENT_AMD]:
        if f.exists():
            data = json.load(open(f))
            for p in (data if isinstance(data, list) else data.get('profiles', [])):
                u = normalise_url(p.get('url', ''))
                if u:
                    sent.add(u)
                sent.add(p.get('name', '').lower())
    return sent

def update_sent(url, name):
    """Append to AMD sent tracking."""
    data = []
    if SENT_AMD.exists():
        data = json.load(open(SENT_AMD))
        if isinstance(data, dict) and 'profiles' in data:
            data = data['profiles']
    data.append({"url": url, "name": name, "sent": datetime.now().isoformat()})
    json.dump(data, open(SENT_AMD, 'w'), indent=2)

def load_gpu_cases():
    data = json.load(open(GPU_CASES))
    if isinstance(data, dict) and 'use_cases' in data:
        return data['use_cases']
    return data if isinstance(data, list) else []

def load_addresses():
    """Load address DB. Returns list of (addr1, addr2, city, prov, zip)."""
    addrs = []
    if ADDR_FILE.exists():
        for line in open(ADDR_FILE).read().strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('|')
            if len(parts) >= 3:
                addrs.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else '',
                              parts[2].strip(), parts[3].strip() if len(parts) > 3 else DEFAULT_PROVINCE,
                              parts[4].strip() if len(parts) > 4 else ''))
    return addrs

def load_city_univ():
    data = json.load(open(CITIES_UNIV))
    return data.get('cities', data) if isinstance(data, dict) else data

def pick_university(city):
    """Pick a university matching the city."""
    cu = load_city_univ()
    if isinstance(cu, dict):
        for city_name, univs in cu.items():
            if city_name.lower() == city.lower():
                return random.choice(univs)
        # Fallback to first city's universities
        first = next(iter(cu.values()), None)
        return random.choice(first) if first else "Universitas Indonesia"
    # Legacy list-of-dicts format
    for entry in cu:
        if entry.get('city', '').lower() == city.lower():
            return random.choice(entry['universities'])
    return random.choice(cu[0]['universities']) if cu else "Universitas Indonesia"

def yahoo_search(query, page=1):
    """Search Yahoo via curl with Chrome UA. Returns list of LinkedIn URLs."""
    query_enc = query.replace(' ', '+')
    url = f"https://search.yahoo.com/search?p={query_enc}&b={(page-1)*10+1}&pz=10"
    
    try:
        r = subprocess.run(['curl', '-s', '-L', url, '-A', UA,
            '--max-time', '15', '--compressed'],
            capture_output=True, text=True, timeout=20)
    except:
        return []
    
    html = r.stdout
    results = []
    
    # Yahoo redirect links
    for ru in re.findall(r'RU=([^/]+%2f[^"&]+)', html):
        decoded = urllib.parse.unquote(ru).replace('%2f', '/')
        if 'linkedin.com/in/' in decoded:
            results.append(decoded.split('&')[0])
    
    # Direct links
    for href in re.findall(r'href=["\'](https?://(?:www\.|id\.|en\.)?linkedin\.com/in/[a-zA-Z0-9_-]+)', html):
        results.append(href.split('?')[0])
    
    return results

def extract_name_from_slug(slug):
    """Convert LinkedIn slug to display name."""
    parts = slug.split('-')
    # Remove trailing segments that are pure digits only
    while parts and parts[-1].isdigit():
        parts.pop()
    # Remove trailing segments that start with digits (like '20', '14', etc.)
    while parts and parts[-1] and parts[-1][0].isdigit():
        parts.pop()
    # Remove trailing segments that look like hash/ID (letters+digits intermixed, 6+ chars)
    # NOT just trailing numbers (e.g. 'andinip2002' → keep)
    while parts and len(parts[-1]) >= 6 and re.search(r'\d', parts[-1]) and re.search(r'[a-z]', parts[-1], re.I):
        # Only pop if digits are INTERLEAVED (not just trailing)
        last = parts[-1]
        trailing_digits = re.search(r'(\d+)$', last)
        if trailing_digits:
            before_digits = last[:trailing_digits.start()]
            # If everything before digits is letters-only, this is a name+number, not hash
            if re.match(r'^[a-zA-Z]+$', before_digits):
                # If before_digits is a single letter, it's a hash like 'b83857411', not a name
                if len(before_digits) <= 1:
                    parts.pop()
                break
        parts.pop()
    # For parts mixed with trailing digits (e.g. 'bagus20', 'adityaputra14'), strip trailing digits
    if parts:
        parts[-1] = re.sub(r'\d+$', '', parts[-1])
    # Remove empty parts
    parts = [p for p in parts if p]
    if not parts:
        return "User"
    # Deduplicate repeated name (e.g. 'khoiriyah-khoiriyah' → 'Khoiriyah')
    if len(parts) >= 2 and len(set(p.lower() for p in parts)) == 1:
        parts = parts[:1]
    return ' '.join(p.capitalize() for p in parts)

def amd_json(first, last, email, domain, url, address, city, prov, zipcode, phone, univ, gpu_text,
             job_func=None, affil_type=None):
    """Generate one AMD registration JSON."""
    jf = job_func or "Student"
    at = affil_type or "Student"
    return {
        "profiles": [{
            "name": "AMD Create Account",
            "urlPattern": "amd.com",
            "inputs": [
                {"key": "location", "label": "Location / Country", "value": "Indonesia"},
                {"key": "jobFunction", "label": "Job Function", "value": jf},
                {"key": "productNeeded", "label": "Product Needed", "value": "AMD Dev Cloud"},
                {"key": "affiliationType", "label": "Affiliation Type", "value": at},
                {"key": "howToUse", "label": "How do you plan to use", "default": gpu_text}
            ],
            "steps": [
                {"name": "Langkah 1 \u2013 Buat Akun", "fields": [
                    {"label": "First Name", "value": first},
                    {"label": "Last Name", "value": last},
                    {"label": "E-mail", "value": email},
                    {"label": "Preferred Language", "value": "English"}
                ]},
                {"name": "Langkah 2 \u2013 Aktivasi (pakai Access Token)", "fields": [
                    {"label": "Access Token", "value": "[[token]]"},
                    {"label": "Password", "value": PASSWORD},
                    {"label": "Confirm Password", "value": PASSWORD}
                ]},
                {"name": "Langkah 3 \u2013 Lengkapi Profil", "fields": [
                    {"label": "First Name", "value": first},
                    {"label": "Last Name", "value": last},
                    {"label": "E-mail", "value": email},
                    {"label": "Company Name", "value": univ},
                    {"label": "Address 1", "value": address[0]},
                    {"label": "Address 2", "value": address[1]},
                    {"label": "Location / Country", "value": "Indonesia"},
                    {"label": "City", "value": city},
                    {"label": "State/Province", "value": prov},
                    {"label": "Postal Code", "value": zipcode},
                    {"label": "Phone", "value": phone},
                    {"label": "Job Function", "value": jf},
                    {"label": "Product Needed", "value": "AMD Dev Cloud"},
                    {"label": "Affiliation Type", "value": at},
                    {"label": "How do you plan to use", "value": gpu_text},
                    {"label": "Profile 1", "value": url}
                ]}
            ]
        }]
    }

# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sent = load_sent()
    gpu_cases = load_gpu_cases()
    addresses = load_addresses()
    
    # ── Stage 1: Yahoo Search ──
    queries = [
        'site:id.linkedin.com/in "Open to Work" mahasiswa',
        'site:id.linkedin.com/in "#OpenToWork" mahasiswa',
        'site:id.linkedin.com/in "Open to Work" fresh graduate',
        'site:linkedin.com/in "Open to Work" Indonesia mahasiswa',
        'site:linkedin.com/in "Open to Work" mahasiswa fresh graduate Indonesia',
    ]
    
    fresh = []
    seen_slugs = set()
    
    for query in queries:
        urls = yahoo_search(query)
        for url in urls:
            u = normalise_url(url)
            slug = slug_from_url(url)
            if not slug or slug in seen_slugs or slug in sent or u in sent:
                continue
            seen_slugs.add(slug)
            name = extract_name_from_slug(slug)
            if name.lower() in sent:
                continue
            if is_bad_name(name, slug):
                continue
            fresh.append({"url": u, "slug": slug, "name": name})
        
        if len(fresh) >= N_TARGET * 2:
            break
    
    print(f"[Yahoo] Found {len(fresh)} fresh profiles from Yahoo search")
    
    # ── Stage 2: Generate JSON ──
    generated = 0
    used_gpu = set()
    
    for i, profile in enumerate(fresh[:N_TARGET]):
        first, last = split_name(profile['name'])
        domain = random.choice(DOMAINS)
        email_local = (first + last + str(random.randint(10000,99999))).lower().replace(' ', '')
        if not last:
            email_local = first.lower()
        email = f"{email_local}@{domain}"
        
        # Pick address
        if addresses:
            addr = random.choice(addresses)
            city = addr[2]
            prov = addr[3]
            zipcode = addr[4]
            addr_data = (addr[0], addr[1])
        else:
            addr_data = ("Jl. Raya", "")
            city = DEFAULT_CITY
            prov = DEFAULT_PROVINCE
            zipcode = f"{random.randint(10000,99999)}"
        
        phone = f"{PHONE_PREFIX}{random.randint(1000000,9999999)}"
        univ = pick_university(city)
        
        # Pick GPU case (no repeats)
        available = [c for c in gpu_cases if c not in used_gpu]
        if not available:
            available = gpu_cases
        gpu_text = random.choice(available)
        used_gpu.add(gpu_text)
        
        # Generate JSON
        data = amd_json(first, last, email, domain, profile['url'],
                        addr_data, city, prov, zipcode, phone, univ, gpu_text)
        
        fname = f"{i+1:02d}_{first}_{last}.json".replace(' ', '_').lower()
        if not last:
            fname = f"{i+1:02d}_{first}.json".lower()
        
        json.dump(data, open(OUT_DIR / fname, 'w'), indent=2, ensure_ascii=False)
        update_sent(profile['url'], profile['name'])
        generated += 1
    
    # ── Stage 3: ZIP ──
    zip_path = OUT_DIR / "li10_fresh_yahoo.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(OUT_DIR.glob("*.json")):
            zf.write(f, f.name)
    
    print(f"\n✅ Generated {generated} JSON files → {zip_path}")
    print("\nProfiles:")
    for i, profile in enumerate(fresh[:generated]):
        first, last = split_name(profile['name'])
        domain_display = DOMAINS[i % 2]
        print(f"  {i+1}. {profile['name']} ({profile['url']}) → @{domain_display}")

if __name__ == "__main__":
    main()
