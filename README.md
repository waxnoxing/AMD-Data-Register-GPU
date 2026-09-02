# LinkedIn Open to Work Skill → AMD JSON Pipeline

**Fresh-on-demand** LinkedIn profile search (Indonesia, Open to Work, **individual only**) → city-matched university → 25 AMD-friendly use cases → AMD registration JSON generator.

## Pipeline

```
Search (CloakBrowser Google dork) → Dedup (sent_profiles × 2) → City-Univ match → 
GPU use case (random from 25) → AMD JSON (1 file/profil) → ZIP → Telegram
```

## Files

```
├── SKILL.md                     # Hermes skill — agent instructions
├── scripts/
│   ├── search_li.py             # Multi-engine search + company filter
│   └── combo_unique.py          # Search → dedup → format + AMD JSON
├── amd-register-sugab-scripts/
│   └── amd_register_json.py     # Standalone AMD JSON generator
├── data/
│   ├── address.txt              # Indonesian addresses (pipe-separated)
│   ├── cities_univ.json         # City → university mapping
│   ├── gpu_use_cases.json       # 25 AMD-friendly use case texts
│   ├── linkedin_cache.json      # Auto-generated search cache
│   └── sent_profiles.json       # Auto-generated sent tracking
```

## Key Features

- **Individual-only filter** — 5-layer company/recruiter rejection
- **City-matched university** — Depok→UI/Gunadarma, Surabaya→Airlangga, etc.
- **25 AMD-approval-optimized use cases** — all education/research focused
- **Dual domain support** — `ubsi.biz.id` & `gmailedu.web.id`, random selection
- **Zero stock** — fresh search every request
- **Dedup against BOTH** LI sent + AMD sent tracking

## Usage (Hermes agent)

```bash
# Search fresh via CloakBrowser → dedup → JSON → ZIP → send
# Domain random: ubsi.biz.id / gmailedu.web.id
# Password: PasswordKuat!1
```

## Dependencies

Python 3.11+ stdlib only (json, subprocess, re, random, pathlib, datetime).
No pip install needed. CloakBrowser for search (anti-detection Chromium).

## Repo

https://github.com/waxnoxing/linkedin-open-to-work-skill
