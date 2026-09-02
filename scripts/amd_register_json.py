#!/usr/bin/env python3
"""amd_register_json.py — Generate AMD Developer Cloud registration JSON from LinkedIn profiles

Usage:
  python3 amd_register_json.py                          # 1 profile Indonesia
  python3 amd_register_json.py 5                        # N profiles Indonesia
  python3 amd_register_json.py 5 --country Singapore    # N profiles Singapore
  python3 amd_register_json.py 1 --url "https://..."    # specific profile
  python3 amd_register_json.py --list                   # list available
  python3 amd_register_json.py 3 --domain ubsi.biz.id --password "MyPass!1"
"""

import json, random, sys, re
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path.home() / ".hermes/skills/social-media/linkedin-open-to-work"
AMD_DIR = Path.home() / ".hermes/skills/social-media/amd-register-sugab"
SCRIPTS_DIR = SKILL_DIR / "scripts"
DATA_DIR = AMD_DIR / "data"
SENT_FILE = DATA_DIR / "sent_amd_profiles.json"
GPU_USE_CASES_FILE = Path.home() / ".hermes/data/gpu_use_cases.json"

sys.path.insert(0, str(SCRIPTS_DIR))
from search_li import do_refresh, get_fresh_profiles, normalise_url, extract_name_from_url

# Reuse combo_unique's country-aware helpers
from combo_unique import load_addresses, load_cities_univ, load_gpu_use_cases, match_university


def generate_amd_json(profile, domain="sugabdemy.app", password="PasswordKuat!1", country="Indonesia"):
    """Generate 3-step AMD registration JSON for a profile."""
    name = profile.get('name', '')
    url = profile.get('url', '')

    # Clean email local part
    email_local = re.sub(r'[^a-zA-Z]', '', name).lower()
    email = f"{email_local}@{domain}"

    # Country-specific data
    addresses = load_addresses(country)
    cities_univ = load_cities_univ(country)
    gpu_cases = load_gpu_use_cases()

    if addresses:
        addr = random.choice(addresses)
        city = addr['city']
        address1 = addr['address1']
        address2 = addr['address2']
        province = addr['province']
        zipcode = addr['zip']
    else:
        city = 'Jakarta' if country == 'Indonesia' else 'Singapore'
        address1 = 'Jl. Sudirman No. 1' if country == 'Indonesia' else '1 Rochor Canal Road'
        address2 = '' if country == 'Indonesia' else 'Rochor'
        province = 'DKI Jakarta' if country == 'Indonesia' else 'Singapore'
        zipcode = '10220' if country == 'Indonesia' else '188504'

    university = match_university(city, cities_univ, country)
    gpu_case = random.choice(gpu_cases)

    phone = (
        f"628{random.randint(100000000, 999999999)}"
        if country == "Indonesia"
        else f"65{random.randint(10000000, 99999999)}"
    )

    first_name = name.split()[0] if name.split() else name
    last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''

    return {
        "profiles": [{
            "name": "AMD Create Account",
            "urlPattern": "amd.com",
            "steps": [
                {
                    "name": "Langkah 1 – Buat Akun",
                    "fields": [
                        {"label": "First Name", "value": first_name},
                        {"label": "Last Name", "value": last_name},
                        {"label": "E-mail", "value": email},
                        {"label": "Preferred Language", "value": "English"},
                        {"label": "Location", "value": country},
                    ]
                },
                {
                    "name": "Langkah 2 – Aktivasi",
                    "fields": [
                        {"label": "Access Token", "value": ""},
                        {"label": "Password", "value": password},
                        {"label": "Confirm Password", "value": password},
                    ]
                },
                {
                    "name": "Langkah 3 – Profil & Credit Request",
                    "fields": [
                        {"label": "Company Name", "value": university},
                        {"label": "Address 1", "value": address1},
                        {"label": "Address 2", "value": address2},
                        {"label": "City", "value": city},
                        {"label": "State/Province", "value": province},
                        {"label": "Postal Code", "value": zipcode},
                        {"label": "Phone", "value": phone},
                        {"label": "Job Function", "value": "Student"},
                        {"label": "Product Needed", "value": "AMD Developer Cloud"},
                        {"label": "Affiliation Type", "value": "School"},
                        {"label": "How do you plan to use", "value": gpu_case},
                        {"label": "Profile 1", "value": url},
                    ]
                }
            ]
        }]
    }


def main():
    args = sys.argv[1:]
    count = 1
    domain = "sugabdemy.app"
    password = "PasswordKuat!1"
    specific_url = None
    country = "Indonesia"

    # Parse args
    i = 0
    while i < len(args):
        if args[i].isdigit():
            count = int(args[i])
        elif args[i] == '--url' and i + 1 < len(args):
            specific_url = args[i + 1]
            i += 1
        elif args[i] == '--domain' and i + 1 < len(args):
            domain = args[i + 1]
            i += 1
        elif args[i] == '--password' and i + 1 < len(args):
            password = args[i + 1]
            i += 1
        elif args[i] == '--country' and i + 1 < len(args):
            country = args[i + 1]
            i += 1
        elif args[i] == '--list':
            profiles = get_fresh_profiles(count=50, exclude_sent=False, country=country)
            for p in profiles:
                print(f"{p['name']} | {p['url']}")
            sys.exit(0)
        i += 1

    # Get profiles
    if specific_url:
        profiles = [{'name': extract_name_from_url(specific_url), 'url': specific_url}]
    else:
        profiles = get_fresh_profiles(count=count, exclude_sent=True, country=country)
        if not profiles:
            print(f"[amd] No profiles in cache for {country}, searching...")
            do_refresh(target_count=max(count * 3, 30), country=country)
            profiles = get_fresh_profiles(count=count, exclude_sent=True, country=country)

    if not profiles:
        print("[amd] No profiles available. All engines may be blocked.")
        sys.exit(1)

    # Generate JSON files
    output_dir = Path.cwd()
    generated = []

    for profile in profiles[:count]:
        amd_json = generate_amd_json(profile, domain=domain, password=password, country=country)
        name = profile.get('name', 'unknown').replace(' ', '_')
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        filename = f"amd-register-{safe_name}.json"
        filepath = output_dir / filename

        json.dump(amd_json, open(filepath, 'w'), indent=2, ensure_ascii=False)
        generated.append(filepath)
        print(f"Generated: {filename} ({profile.get('name', '')})")

    # Mark sent
    sent_data = [{'name': p.get('name', ''), 'url': p.get('url', '')} for p in profiles[:count]]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SENT_FILE.exists():
        sent = json.load(open(SENT_FILE))
    else:
        sent = []
    sent.extend(sent_data)
    json.dump(sent, open(SENT_FILE, 'w'), indent=2, ensure_ascii=False)

    print(f"\nDone: {len(generated)} JSON files generated.")
    print(f"Sent tracking: {SENT_FILE}")


if __name__ == '__main__':
    main()
