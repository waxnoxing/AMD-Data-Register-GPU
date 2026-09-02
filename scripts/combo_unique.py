#!/usr/bin/env python3
"""combo_unique.py — Get fresh LinkedIn profiles (Open to Work, individual, multi-country)

Usage:
  python3 combo_unique.py                        # 5 profiles Indonesia
  python3 combo_unique.py 10                      # 10 profiles Indonesia
  python3 combo_unique.py 10 --country Singapore  # 10 profiles Singapore
  python3 combo_unique.py 5 --country Malaysia    # 5 profiles Malaysia
  python3 combo_unique.py 10 --json               # JSON output
  python3 combo_unique.py 10 --amd-json           # AMD pipeline JSON files
"""

import json, random, sys, re
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path.home() / ".hermes/skills/social-media/linkedin-open-to-work"
SCRIPTS_DIR = SKILL_DIR / "scripts"
DATA_DIR = SKILL_DIR / "data"
GPU_USE_CASES_FILE = Path.home() / ".hermes/data/gpu_use_cases.json"
SENT_FILE = DATA_DIR / "sent_profiles.json"
AMD_SENT_FILE = Path.home() / ".hermes/skills/social-media/amd-register-sugab/data/sent_amd_profiles.json"

sys.path.insert(0, str(SCRIPTS_DIR))
from search_li import do_refresh, get_fresh_profiles, mark_sent, normalise_url, extract_name_from_url


def get_country_data_files(country):
    """Get data file paths for a specific country."""
    # Country code mapping for file naming
    cc_map = {"Singapore": "sg", "Malaysia": "my", "Indonesia": ""}
    cc = cc_map.get(country, country.lower().replace(' ', '_'))
    
    if not cc or country == "Indonesia":
        return {
            'address': DATA_DIR / "address.txt",
            'cities_univ': DATA_DIR / "cities_univ.json",
        }
    return {
        'address': DATA_DIR / f"address_{cc}.txt",
        'cities_univ': DATA_DIR / f"cities_univ_{cc}.json",
    }


def load_addresses(country="Indonesia"):
    """Load address database for a specific country."""
    files = get_country_data_files(country)
    addr_file = files['address']
    if not addr_file.exists():
        return []
    addresses = []
    for line in open(addr_file):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('|')
        if len(parts) >= 5:
            addresses.append({
                'address1': parts[0].strip(),
                'address2': parts[1].strip(),
                'city': parts[2].strip(),
                'province': parts[3].strip(),
                'zip': parts[4].strip(),
            })
    return addresses


def load_cities_univ(country="Indonesia"):
    """Load city -> university mapping for a specific country."""
    files = get_country_data_files(country)
    cu_file = files['cities_univ']
    if not cu_file.exists():
        return {}
    return json.load(open(cu_file))


def load_gpu_use_cases():
    """Load GPU use case templates."""
    if not GPU_USE_CASES_FILE.exists():
        return [
            "I am learning AI agent development and need GPU access to complete my school projects and improve my grades.",
            "As a computer science student, I am building an AI agent for my final project and need GPU resources.",
            "I am studying artificial intelligence and working on a school assignment that requires GPU computing.",
            "I need GPU access for my university coursework in machine learning and deep learning.",
            "As a student learning AI development, I require GPU resources for my academic projects.",
            "I am a graduate student researching AI agents for my thesis and need GPU access.",
            "I am taking a course on artificial intelligence and need GPU access for assignments.",
            "As part of my computer science degree, I am developing an AI-powered application that needs GPU.",
            "I am learning about autonomous AI agents in my university program and need GPU resources.",
            "I need GPU resources for my academic projects in the AI field to improve my grades.",
        ]
    raw = json.load(open(GPU_USE_CASES_FILE))
    # Handle both list and {"use_cases": [...]} formats
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get('use_cases', raw.get('templates', []))
    return []


def match_university(city, cities_univ, country="Indonesia"):
    """Match city with university."""
    city_lower = city.lower()
    for key, unis in cities_univ.items():
        if key.lower() == city_lower:
            return random.choice(unis)
    # Country-appropriate fallback
    fallbacks = {
        "Singapore": ["National University of Singapore", "Nanyang Technological University"],
        "Malaysia": ["Universiti Malaya", "Universiti Kebangsaan Malaysia"],
        "Indonesia": ["Universitas Negeri Jakarta", "Universitas Mercu Buana", "Universitas Trisakti"],
    }
    fb = fallbacks.get(country, fallbacks["Indonesia"])
    return random.choice(fb)


def format_profile(profile, addresses, cities_univ, gpu_cases, country="Indonesia", domain="ubsi.biz.id"):
    """Format a single profile with address + university."""
    url = profile.get('url', '')
    name = profile.get('name', extract_name_from_url(url))

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

    # Build email: firstnamelastname@domain (lowercase, no dots)
    name_clean = re.sub(r'[^a-zA-Z]', '', name).lower()
    email = f"{name_clean}@{domain}"

    return {
        'name': name,
        'first_name': name.split()[0] if name.split() else name,
        'last_name': ' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
        'url': url,
        'email': email,
        'city': city,
        'province': province,
        'address1': address1,
        'address2': address2,
        'zip': zipcode,
        'university': university,
        'gpu_case': gpu_case,
        'phone': f"628{random.randint(100000000, 999999999)}" if country == "Indonesia" else f"65{random.randint(10000000, 99999999)}",
        'country': country,
    }


def print_profile(p):
    """Print profile in label:value format."""
    print(f"Name       : {p['name']}")
    print(f"LinkedIn   : {p['url']}")
    print(f"Email      : {p['email']}")
    print(f"Country    : {p['country']}")
    print(f"City       : {p['city']}")
    print(f"Province   : {p['province']}")
    print(f"University : {p['university']}")
    print(f"Address 1  : {p['address1']}")
    print(f"Address 2  : {p['address2']}")
    print(f"Zip        : {p['zip']}")
    print(f"Phone      : {p['phone']}")
    print(f"Alasan     : {p['gpu_case']}")
    print()


def main():
    args = sys.argv[1:]
    count = 5
    force_search = '--force-search' in args
    json_output = '--json' in args
    amd_json = '--amd-json' in args or '--json-send' in args
    domain = 'ubsi.biz.id'
    password = 'PasswordKuat!1'
    is_send = '--json-send' in args
    country = 'Indonesia'

    # Parse --country
    if '--country' in args:
        try:
            idx = args.index('--country')
            country = args[idx + 1]
            del args[idx:idx+2]
        except:
            pass

    # Parse count
    for a in args:
        if a.isdigit():
            count = int(a)
            break

    if '--count' in args:
        try:
            idx = args.index('--count')
            count = int(args[idx + 1])
        except:
            pass

    # Parse domain
    if '--domain' in args:
        try:
            idx = args.index('--domain')
            domain = args[idx + 1]
        except:
            pass

    # Always search fresh — no stock/cache-first
    print(f"[combo_unique] Searching fresh profiles for {country}...")
    do_refresh(target_count=max(count * 3, 30), country=country)

    # Get fresh profiles (exclude already sent)
    profiles = get_fresh_profiles(count=count, exclude_sent=True, country=country)

    if not profiles:
        print("[combo_unique] Still no fresh profiles found.")
        sys.exit(1)

    # Load country-specific data
    addresses = load_addresses(country)
    cities_univ = load_cities_univ(country)
    gpu_cases = load_gpu_use_cases()

    # Format
    results = []
    for profile in profiles[:count]:
        p = format_profile(profile, addresses, cities_univ, gpu_cases, country=country, domain=domain)
        results.append(p)

    # Output
    if json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif amd_json:
        # Generate AMD JSON files
        amd_dir = Path.home() / ".hermes/skills/social-media/amd-register-sugab"
        for i, p in enumerate(results, 1):
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', p['name'])
            filename = f"amd-register-{safe_name}.json"

            amd_json_data = {
                "profiles": [{
                    "name": "AMD Create Account",
                    "urlPattern": "amd.com",
                    "inputs": [
                        {"key": "location", "label": "Location / Country"},
                        {"key": "jobFunction", "label": "Job Function"},
                        {"key": "productNeeded", "label": "Product Needed"},
                        {"key": "affiliationType", "label": "Affiliation Type"},
                        {"key": "howToUse", "label": "How do you plan to use", "default": p['gpu_case']}
                    ],
                    "steps": [
                        {
                            "name": "Langkah 1 – Buat Akun",
                            "fields": [
                                {"label": "First Name", "value": p['first_name']},
                                {"label": "Last Name", "value": p['last_name']},
                                {"label": "E-mail", "value": p['email']},
                                {"label": "Preferred Language", "value": "English"},
                            ]
                        },
                        {
                            "name": "Langkah 2 – Aktivasi (pakai Access Token)",
                            "fields": [
                                {"label": "Access Token", "value": "[[token]]"},
                                {"label": "Password", "value": password},
                                {"label": "Confirm Password", "value": password},
                            ]
                        },
                        {
                            "name": "Langkah 3 – Lengkapi Profil",
                            "fields": [
                                {"label": "First Name", "value": p['first_name']},
                                {"label": "Last Name", "value": p['last_name']},
                                {"label": "E-mail", "value": p['email']},
                                {"label": "Company Name", "value": p['university']},
                                {"label": "Address 1", "value": p['address1']},
                                {"label": "Address 2", "value": p['address2']},
                                {"label": "Location / Country", "value": p['country']},
                                {"label": "City", "value": p['city']},
                                {"label": "State/Province", "value": p['province']},
                                {"label": "Postal Code", "value": p['zip']},
                                {"label": "Phone", "value": p['phone']},
                                {"label": "Job Function", "value": "Student"},
                                {"label": "Product Needed", "value": "AMD Dev Cloud"},
                                {"label": "Affiliation Type", "value": "Student"},
                                {"label": "How do you plan to use", "value": p['gpu_case']},
                                {"label": "Profile 1", "value": p['url']},
                            ]
                        }
                    ]
                }]
            }

            amd_dir.mkdir(parents=True, exist_ok=True)
            json.dump(amd_json_data, open(amd_dir / filename, 'w'), indent=2, ensure_ascii=False)
            print(f"Generated: {filename} ({p['name']})")

        # Update AMD sent tracking
        amd_sent_file = amd_dir / "data" / "sent_amd_profiles.json"
        amd_sent = []
        if amd_sent_file.exists():
            amd_sent = json.load(open(amd_sent_file))
        for p in results:
            amd_sent.append({
                'name': p['name'],
                'url': p['url'],
                'sent_at': datetime.now().isoformat()
            })
        amd_sent_file.parent.mkdir(parents=True, exist_ok=True)
        json.dump(amd_sent, open(amd_sent_file, 'w'), indent=2)

        print(f"\n[combo_unique] {len(results)} AMD JSON files generated.")

    else:
        for p in results:
            print_profile(p)

    # Mark sent
    mark_sent([{'name': p['name'], 'url': p['url']} for p in results])
    if not is_send:
        print(f"[combo_unique] Sent {len(results)} profiles, marked as used.")


if __name__ == '__main__':
    main()
