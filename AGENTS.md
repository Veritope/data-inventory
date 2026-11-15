# Using this inventory from an agent or pipeline

This directory is built to be consumed by machines, not just read. If you are an
automated agent planning data ingestion, start here.

## The one file to load
[`index.json`](index.json) — a flat list of every catalogued dataset with
normalized, derived fields. Everything else is generated from the same catalog.

Each record carries, in addition to the curated fields:
- `open_access` (bool)
- `agent_automatable` (bool) — open **and** has a programmatic endpoint
- `ingest_endpoint` — the URL to pull from (`api` → `download_url` → `landing_url`)
- `feeds_stages` — research-agenda stages (0–5) the dataset supports

## Typical queries
```python
import json
data = json.load(open("index.json"))

# Everything an agent can pull today, no human in the loop:
ready = [d for d in data if d["agent_automatable"]]

# Presentation-program sources with an open license:
pres = [d for d in data
        if "presentation" in d["relevance"]["programs"] and d["open_access"]]

# Canine data (the scarce, high-priority slice):
dog = [d for d in data if "dog" in d["species"]]

# Commercial-safe only (Veritope is for-profit) — skip unknown/restricted:
commercial_ok = [d for d in data if d["commercial_use"] is True]

# Anything that still needs a data-use agreement before use:
controlled = [d for d in data if d["access"] == "controlled-access"]
```

## Before ingesting any dataset
1. **Check `license` and `caveats`.** Some sources forbid redistribution or ML
   training. Honor it. The catalog flags these, but re-read the source terms.
2. **Check `access`.** `controlled-access` means a DUA/dbGaP/EGA approval is
   required first; do not attempt to scrape around it.
3. **Respect `agent_access`.** It records auth needs, rate limits, and whether
   bulk download exists. Prefer bulk endpoints over scraping.
4. **Record provenance.** Keep the `id`, the source URL, and the version/date you
   pulled, so results stay reproducible and citable.

## Rebuilding
After editing any `catalog/*.yaml`:
```bash
python3 scripts/build_index.py
```
It validates the catalog (non-zero exit on error) and regenerates all indexes.
