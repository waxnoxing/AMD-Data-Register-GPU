---
name: amd-data-register-gpu
description: "AMD Developer Cloud register generator — GitHub-first: find GitHub users w/ LinkedIn in profile → AMD JSON (P1 GitHub, P2 LinkedIn). Concurrent, auto-dedup, rate-limit safe."
---

# AMD Data Register GPU — GitHub-First Pipeline

Generate AMD Account JSON for GPU developer-cloud registration. Primary source: **GitHub users** whose profile lists a LinkedIn URL.

## Output Shape (Step 3)

```json
{"key": "profile1", "label": "Profile 1", "value": "https://github.com/<login>", "type": "url"},
{"key": "profile2", "label": "Profile 2", "value": "https://linkedin.com/in/<slug>", "type": "url"}
```
`key` + `type` REQUIRED — autofill plugin maps fields via `key`.

## Primary: gh_li_gen.py (GitHub-first)

```bash
python3 ~/.hermes/skills/social-media/linkedin-open-to-work/scripts/gh_li_gen.py
# → /tmp/gh10_fresh/*.json → ZIP → send
```

Pipeline:
1. **GitHub Search API** — `linkedin location:Indonesia language:<lang>` (query pool rotates: Python, JavaScript, Java, Go, TypeScript, PHP)
2. **Dedup** vs `sent_amd_profiles.json` (GitHub-url + LinkedIn-url)
3. **Concurrent profile fetch** (ThreadPool 5) → name + LinkedIn URL from profile HTML
4. **Filter** — keep only users whose profile lists a real LinkedIn URL (skip no-LI, skip dup-LI)
5. **AMD JSON** — full fields + P1=GitHub + P2=LinkedIn
6. **Auto-write tracker** `sent_amd_profiles.json`
7. **Verify + ZIP + Send**

### Rate-limit (optional speed boost)
Unauth = search 10/h, core 60/h (enough for one batch). Set token for 30×:
```bash
export GITHUB_TOKEN=<fine-grained read:user token>
python3 gh_li_gen.py
```
Token = env only, never saved/pushed.

## Scripts

| Script | Purpose |
|--------|---------|
| `gh_li_gen.py` | **PRIMARY** — GitHub-first AMD JSON, concurrent, auto-dedup |
| `test_gh_li_gen.py` | Self-check (6 assert) — no network |
| `li_gen_github.py` | Legacy LinkedIn-first pipeline (CamoFox + Yahoo) |
| `find_github.py` | GitHub finder by name (CamoFox Yahoo, score) |
| `gen_fresh_li.py` | Core helpers: amd_json, split_name, load_sent, update_sent |
| `gen_use_cases.py` | Generate 1000 GPU use-case answers |
| `amd_register_json.py` | Legacy AMD JSON builder |
| `ddg_lite_search.py` / `search_li.py` | Search engines (dedup/create) |

## Data Files

- `data/address.txt` — Indonesian addresses (pipe-delimited; SG variant `address_sg.txt`)
- `data/cities_univ.json` — city → university mapping
- `data/gpu_use_cases.json` — curated answers
- `data/use_case_answers.json` — 1000 generated answers
- `data/sent_amd_profiles.json` — dedup tracker (auto-written; local, NOT in repo)

## Rules

- Always dedup: `load_sent()` — skip if GH url OR LinkedIn url already sent
- `How do you plan to use` picks from use-case pool (rotate)
- Verify: P1=P2 not swapped, valid URLs, city+address+zip non-empty, emails unique
- No double names (first==last), no short names
- Zip folder → `hermes send -t telegram "MEDIA:/path.zip"`