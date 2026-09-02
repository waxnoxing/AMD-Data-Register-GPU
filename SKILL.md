---
name: linkedin-open-to-work
description: "Fresh LinkedIn profile search + GitHub matching → AMD register JSON (Profile 1 LinkedIn, Profile 2 GitHub). CamoFox bypass. 1000 GPU use-case answers included."
---

# LinkedIn Open-to-Work → AMD Register Pipeline

Fresh on-demand search → GitHub-matched profiles → AMD JSON files.

## ⚡ Quick Action

When user asks "10 linkedin fresh dan lengkap" → execute immediately:

**Primary method (CamoFox browser + Yahoo):**
```bash
cd /tmp && python3 ~/.hermes/skills/social-media/linkedin-open-to-work/scripts/li_gen_github.py
# → /tmp/amd10_fresh/*.json → ZIP → send
```

## Pipeline

1. **LinkedIn Search** — CamoFox browser port 9377 → Yahoo `site:id.linkedin.com/in "Open to Work" <profession>`
2. **Dedup** — `load_sent()` vs `sent_amd_profiles.json` (flat list)
3. **Name Fix** — `extract_name_from_slug()` → `split_name()` (strip hash, digit, dedup)
4. **GitHub Match** — `find_github(first, last)` via CamoFox Yahoo (score: 4=full, 2=partial, 0=none)
5. **AMD JSON** — complete fields: address, phone, city, univ, GPU reason, `Profile 1` LinkedIn, `Profile 2` GitHub, `How do you plan to use` from use-case pool
6. **Verify + ZIP + Send**

## JSON Format (Step 3)

```json
{"label": "Profile 1", "value": "https://linkedin.com/in/<slug>"},
{"label": "Profile 2", "value": "https://github.com/<slug>"}
```
No `key`, no `type` fields.

## Scripts

| Script | Purpose |
|--------|---------|
| `li_gen_github.py` | Full pipeline: search → match GitHub → generate 10 AMD JSON |
| `find_github.py` | Standalone GitHub finder (Yahoo CamoFox, score-based) |
| `gen_use_cases.py` | Generate 1000 unique GPU use-case answers (JSON) |
| `gen_fresh_li.py` | Core helpers: name split, AMD JSON, dedup |
| `search_li.py` | Multi-engine LinkedIn search |
| `ddg_lite_search.py` | DDG Lite CDP (AWS bypass) |

## Data Files

- `data/address.txt` — 28 Indonesian addresses (pipe-delimited)
- `data/cities_univ.json` — city → university mapping
- `data/gpu_use_cases.json` — 25 curated answers (English)
- `data/use_case_answers.json` — 1000 generated answers
- `data/sent_amd_profiles.json` — dedup tracking (flat list)

## CamoFox Setup (primary method)

```bash
cd /tmp && git clone https://github.com/jo-inc/camofox-browser
cd camofox-browser && npm install && node server.js  # port 9377
```

## Rules

- Profile 2 (GitHub) must include — score ≥2 = visible match, skip if none
- `How do you plan to use` field must pick from `gpu_use_cases.json` or `use_case_answers.json` (rotate, no reuse same session)
- Zip one folder, `hermes send -t telegram "MEDIA:/path.zip"`
- Verify no double names (first_name == last_name), valid URLs, city+address+zip non-empty
- Use `load_sent()` dedup always
