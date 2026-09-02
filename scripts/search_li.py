#!/usr/bin/env python3
"""
search_li.py — Multi-engine LinkedIn profile search (Indonesia, Open to Work, individual only)

Usage:
  python3 search_li.py                  # search + print results
  python3 search_li.py --refresh --count 50   # refresh cache with N profiles
  python3 search_li.py --list-sources   # list engines + queries
"""

import subprocess
import json
import re
import random
import sys
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / ".hermes/skills/social-media/linkedin-open-to-work/data"
CACHE_FILE = DATA_DIR / "linkedin_cache.json"
SENT_FILE = DATA_DIR / "sent_profiles.json"
AMD_SENT_FILE = Path.home() / ".hermes/skills/social-media/amd-register-sugab/data/sent_amd_profiles.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# Default queries for Indonesia
DEFAULT_QUERIES = [
    'site:linkedin.com/in "Open to Work" Indonesia "Lokasi:" -Australia -Singapore -Malaysia',
    'site:linkedin.com/in "Open to Work" "Indonesia" "fresh graduate" -company -pt -CV',
    'site:linkedin.com/in "Open to Work" Indonesia mahasiswa -company -pt',
    'site:linkedin.com/in "Open to Work" Indonesia "mahasiswa" -perusahaan -CV',
    'site:linkedin.com/in "Open to Work" "Sedang mencari" Indonesia',
    'site:linkedin.com/in "Open to Work" Indonesia teknik informatika -company',
    'site:linkedin.com/in "Open to Work" Indonesia "data analyst" -company -pt',
    'site:linkedin.com/in "Open to Work" Indonesia "machine learning" -company',
    'site:linkedin.com/in "Open to Work" Indonesia "software engineer" -company -pt',
    'site:linkedin.com/in "Open to Work" Indonesia "freshgraduate" -company -pt',
]

# Country-agnostic queries (replace COUNTRY placeholder)
COUNTRY_QUERIES = [
    'site:linkedin.com/in "Open to Work" COUNTRY',
    'site:linkedin.com/in "Open to Work" COUNTRY "fresh"',
    'site:linkedin.com/in "Open to Work" COUNTRY "student"',
    'site:linkedin.com/in "Open to Work" COUNTRY "looking"',
    'site:linkedin.com/in "Open to Work" COUNTRY graduate',
    'site:linkedin.com/in "Open to Work" COUNTRY "available"',
    'site:linkedin.com/in "Open to Work" COUNTRY "software"',
    'site:linkedin.com/in "Open to Work" COUNTRY "data"',
    'site:linkedin.com/in "Open to Work" COUNTRY "engineer"',
    'site:linkedin.com/in "Open to Work" COUNTRY "university"',
]


def get_queries(country):
    """Get queries for a specific country."""
    if country == "Indonesia":
        return DEFAULT_QUERIES
    return [q.replace("COUNTRY", country) for q in COUNTRY_QUERIES]

# Company keywords to filter out
COMPANY_KEYWORDS = [
    'pt ', 'pt.', 'cv ', 'cv.', 'tbk', 'persero', 'group', 'community',
    'jobs', 'job', 'career', 'hiring', 'vacancy', 'recruitment',
    'indojob', 'jobstreet', 'kalibrr', 'glint', 'topcompany',
]

# Generic slugs to skip
SKIP_SLUGS = ['open-to-work', 'welcom', 'welcome', 'jobs', 'career']


def extract_name_from_url(url):
    """Extract name from LinkedIn slug."""
    try:
        slug = url.rstrip('/').split('/')[-1]
        parts = slug.split('-')
        # Pop trailing segments with digits
        while parts and re.search(r'\d', parts[-1]):
            parts.pop()
        if not parts:
            return 'Unknown'
        # If single part with no separator
        if len(parts) == 1:
            return parts[0].capitalize()
        return ' '.join(p.capitalize() for p in parts)
    except:
        return 'Unknown'


def is_company_profile(url, snippet):
    """Check if profile is a company page."""
    combined = (url + ' ' + snippet).lower()
    return any(kw in combined for kw in COMPANY_KEYWORDS)


def search_ddg(query, timeout=15):
    """Search via DuckDuckGo Lite — most reliable on AWS IP."""
    url = f"https://lite.duckduckgo.com/lite/?q={query.replace(' ', '+')}"
    try:
        r = subprocess.run(
            ['curl', '-s', '-L', url, '-A', UA,
             '--max-time', str(timeout), '--compressed'],
            capture_output=True, text=True, timeout=timeout + 5
        )
        html = r.stdout
        results = []
        # DDG lite: links are in redirect URLs
        links = re.findall(r'href="[^"]*uddg=([^"&]+)"', html)
        for encoded_url in links:
            try:
                decoded = encoded_url.replace('%3a', ':').replace('%2f', '/')
                decoded = re.sub(r'^///+', 'https://', decoded)
                if 'linkedin.com/in/' in decoded:
                    results.append(decoded)
            except:
                continue
        # Also check direct links
        direct_links = re.findall(r'https?://(?:www\.|id\.)?linkedin\.com/in/[a-zA-Z0-9_-]+', html)
        results.extend(direct_links)
        return results
    except:
        return []


def search_yahoo(query, timeout=15):
    """Search via Yahoo."""
    url = f"https://search.yahoo.com/search?p={query.replace(' ', '+')}"
    try:
        r = subprocess.run(
            ['curl', '-s', '-L', url, '-A', UA,
             '--max-time', str(timeout), '--compressed'],
            capture_output=True, text=True, timeout=timeout + 5
        )
        html = r.stdout
        results = re.findall(r'RU=(https?%3a[^"&]+)', html)
        decoded = []
        for ru in results:
            try:
                url_decoded = re.sub(r'%3a', ':', ru, count=2).replace('%2f', '/')
                url_decoded = re.sub(r'^///+', 'https://', url_decoded)
                if 'linkedin.com/in/' in url_decoded:
                    decoded.append(url_decoded)
            except:
                continue
        # Also direct links
        direct = re.findall(r'https?://(?:www\.|id\.)?linkedin\.com/in/[a-zA-Z0-9_-]+', html)
        decoded.extend(direct)
        return decoded
    except:
        return []


def search_bing(query, timeout=15):
    """Search via Bing."""
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
    try:
        r = subprocess.run(
            ['curl', '-s', '-L', url, '-A', UA,
             '--max-time', str(timeout), '--compressed',
             '-H', 'Accept-Language: en-US,en;q=0.9'],
            capture_output=True, text=True, timeout=timeout + 5
        )
        html = r.stdout
        results = re.findall(r'https?://(?:www\.|id\.|[a-z]+\.)?linkedin\.com/in/[a-zA-Z0-9_-]+', html)
        return results
    except:
        return []


def search_brave(query, timeout=15):
    """Search via Brave Search."""
    url = f"https://search.brave.com/search?q={query.replace(' ', '+')}"
    try:
        r = subprocess.run(
            ['curl', '-s', '-L', url, '-A', UA,
             '--max-time', str(timeout), '--compressed',
             '-H', 'Accept: text/html'],
            capture_output=True, text=True, timeout=timeout + 5
        )
        html = r.stdout
        results = re.findall(r'https?://(?:www\.|id\.)?linkedin\.com/in/[a-zA-Z0-9_-]+', html)
        return results
    except:
        return []


def normalise_url(url):
    """Normalise LinkedIn URL - clean Yahoo redirects and double-prefixes."""
    if not url:
        return url
    url = url.rstrip('/')
    # Fix Yahoo redirect URLs: everything after linkedin.com/in/slug is noise
    m = re.search(r'(https?://(?:www\.|id\.)?linkedin\.com/in/[a-zA-Z0-9_-]+)', url)
    if m:
        url = m.group(1)
    # Fix double-prefix
    url = re.sub(r'^https?://[^/]+/in/https?://', 'https://', url)
    # Standardise to www
    url = re.sub(r'https?://(?:id\.)?linkedin\.com/in/', 'https://www.linkedin.com/in/', url)
    return url


# Company keywords to filter out (checked against slug + extracted name)
COMPANY_KEYWORDS = [
    'pt ', 'pt.', 'cv ', 'cv.', 'tbk', 'persero', 'group', 'community',
    'jobs', 'job', 'career', 'hiring', 'vacancy', 'recruitment',
    'indojob', 'jobstreet', 'kalibrr', 'glint', 'topcompany',
    'hotel', 'restaurant', 'cafe', 'industri', 'manufacturing',
    'consulting', 'technologies', 'solutions', 'services', 'digital',
    'media', 'agency', 'studio', 'academy', 'school', 'course',
    'training', 'institute', 'foundation', 'associat', 'partners',
    'ltd', 'inc', 'corp', 'co ', 'llc', 'plc',
    'openkerja', 'kerja', 'loker', 'lowongan', 'rekrutmen',
    'apartment', 'rumah sakit', 'klinik', 'bank', 'insurance',
    'property', 'real estate', 'travel', 'tour', 'logistic',
    'trading', 'forex', 'crypto exchange', 'marketplace',
    'farming', 'grup', 'perusahaan', 'perseroan',
]

# Generic slugs to skip
SKIP_SLUGS = ['open-to-work', 'welcom', 'welcome', 'jobs', 'career']

# Known company patterns in slugs (1-word or very short = suspicious)
COMPANY_SLUG_PATTERNS = [
    r'^[a-z]+$',           # single word like "openkerja", "enso"
    r'^(pt|cv|tbk|inc|ltd|llc|co)[-\s]',  # starts with company prefix
    r'(group|inc|ltd|llc|corp|co|tbk|pt|cv)$',  # ends with company suffix
]


def is_company_name(name):
    """Check if extracted name looks like a company."""
    name_lower = name.lower().strip()
    for kw in COMPANY_KEYWORDS:
        if kw in name_lower:
            return True
    words = name.split()
    if len(words) <= 1 and len(name) < 15:
        return True
    if len(words) >= 5:
        return True
    return False


def filter_profile(url):
    """Check if URL is a valid individual profile."""
    if not re.match(r'https?://(?:www\.|id\.)?linkedin\.com/in/', url):
        return False
    slug = url.rstrip('/').split('/')[-1].lower()
    if any(s in slug for s in SKIP_SLUGS):
        return False
    if len(slug) < 3:
        return False
    for pattern in COMPANY_SLUG_PATTERNS:
        if re.search(pattern, slug):
            return False
    name = extract_name_from_url(url)
    if is_company_name(name):
        return False
    return True


def do_refresh(target_count=50, verbose=True, country="Indonesia"):
    """Main refresh function — search engines → cache."""
    # Load existing cache
    if CACHE_FILE.exists():
        cache = json.load(open(CACHE_FILE))
    else:
        cache = []

    existing_urls = {normalise_url(p.get('url', '')) for p in cache}
    new_profiles = []

    # Get country-specific queries
    queries = get_queries(country)
    random.shuffle(queries)
    selected_queries = queries[:min(5, len(queries))]

    if verbose:
        print(f"[search_li] Refresh: target={target_count}, cache={len(cache)}, queries={len(selected_queries)}, country={country}")

    engines = [
        ('DDG', search_ddg),
        ('Yahoo', search_yahoo),
        ('Bing', search_bing),
        ('Brave', search_brave),
    ]

    for qi, query in enumerate(selected_queries):
        if len(new_profiles) >= target_count:
            break

        if verbose:
            print(f"[search_li] Q{qi+1}: {query[:80]}...")

        random.shuffle(engines)

        for engine_name, engine_fn in engines:
            if len(new_profiles) >= target_count:
                break

            try:
                urls = engine_fn(query)
            except:
                urls = []

            for url in urls:
                url = normalise_url(url)
                if not filter_profile(url):
                    continue
                if url in existing_urls:
                    continue
                # Check snippet for company keywords — skip if matches
                name = extract_name_from_url(url)
                entry = {
                    'name': name,
                    'url': url,
                    'engine': engine_name,
                    'query': query,
                    'added': datetime.now().isoformat(),
                }
                cache.append(entry)
                new_profiles.append(entry)
                existing_urls.add(url)
                if verbose:
                    print(f"  + {name} ({url})")

            if len(new_profiles) >= target_count:
                break

            # Small delay between engines
            import time
            time.sleep(random.uniform(1.5, 3.5))

    # Save cache
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json.dump(cache, open(CACHE_FILE, 'w'), indent=2, ensure_ascii=False)

    if verbose:
        print(f"[search_li] Done: +{len(new_profiles)} new, total={len(cache)}")

    return new_profiles


def get_sent_urls():
    """Load sent profiles from both LI and AMD trackers."""
    sent = set()
    for f in [SENT_FILE, AMD_SENT_FILE]:
        if f.exists():
            data = json.load(open(f))
            for p in data:
                url = p.get('url', '')
                if url:
                    sent.add(normalise_url(url))
                name = p.get('name', '')
                if name:
                    sent.add(name.lower().strip())
    return sent


def get_fresh_profiles(count=10, exclude_sent=True, country="Indonesia"):
    """Get N fresh profiles from cache, excluding sent."""
    if not CACHE_FILE.exists():
        do_refresh(target_count=max(count * 3, 30), country=country)

    cache = json.load(open(CACHE_FILE)) if CACHE_FILE.exists() else []

    if exclude_sent:
        sent_urls = get_sent_urls()
        available = [p for p in cache if normalise_url(p.get('url', '')) not in sent_urls]
    else:
        available = cache

    random.shuffle(available)
    selected = available[:count]

    return selected


def mark_sent(profiles):
    """Mark profiles as sent."""
    if SENT_FILE.exists():
        sent = json.load(open(SENT_FILE))
    else:
        sent = []
    sent.extend(profiles)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json.dump(sent, open(SENT_FILE, 'w'), indent=2, ensure_ascii=False)


if __name__ == '__main__':
    args = sys.argv[1:]
    country = "Indonesia"

    # Parse --country
    if '--country' in args:
        try:
            idx = args.index('--country')
            country = args[idx + 1]
            # Remove from args to avoid confusion with other flags
            del args[idx:idx+2]
        except:
            pass

    if '--list-sources' in args:
        print("Engines: DDG (primary), Yahoo, Bing, Brave")
        qs = get_queries(country)
        print(f"Queries ({len(qs)}) for {country}:")
        for i, q in enumerate(qs):
            print(f"  {i+1}. {q}")
        sys.exit(0)

    if '--refresh' in args:
        count = 50
        if '--count' in args:
            try:
                idx = args.index('--count')
                count = int(args[idx + 1])
            except:
                pass
        do_refresh(target_count=count, country=country)
    else:
        # Default: get fresh profiles
        count = 10
        profiles = get_fresh_profiles(count=count, country=country)
        for p in profiles:
            print(f"{p['name']} | {p['url']}")
