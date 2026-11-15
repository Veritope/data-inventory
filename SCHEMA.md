# Catalog entry schema

The catalog is the hand-curated source of truth: YAML files in [`catalog/`](catalog/),
one list item per dataset. `scripts/build_index.py` validates these files and
generates the machine-readable indexes (`index.json`, `index.csv`, `stats.json`)
and the grouped views. **Edit the YAML; never edit the generated files.**

## Fields

| field | required | notes |
|---|---|---|
| `id` | yes | short lowercase slug, unique across the whole catalog |
| `name` | yes | human name, with common acronym |
| `category` | yes | one of the controlled values below |
| `species` | yes | list, e.g. `[human, mouse, dog]` |
| `description` | yes | 2–4 sentences on what it actually contains |
| `scale` | no | record counts / size on disk, free text |
| `size_bytes` | no | integer: approximate total download size in bytes, when the source states it (used to total the inventory's data volume) |
| `modalities` | no | data types present, e.g. `[mhc-ligand-elution, binding-assay]` |
| `formats` | no | `[csv, json, api, fastq, mmcif, ...]` |
| `landing_url` | yes | canonical page |
| `download_url` | no | direct bulk download |
| `api` | no | programmatic endpoint base |
| `license` | yes | SPDX id or exact name; `unknown` if genuinely not findable |
| `license_url` | no | link to the license/terms |
| `access` | yes | `open` \| `registration` \| `controlled-access` \| `request` |
| `provenance` | no | `maintainer`, `key_refs` (DOIs) |
| `last_updated` | no | release/version date |
| `relevance` | yes | `programs` (list) + `why` (string) |
| `agent_access` | no | can an automated agent fetch it: auth, rate limits, bulk vs scrape |
| `accessions` | no | list of specific repository accessions (PXD…, GSE…, PRJNA…, phs…, Zenodo DOIs) |
| `caveats` | no | redistribution limits, quality issues, gaps |

### Controlled `category` values
`reference`, `mhc-binding`, `presentation`, `tcr-recognition`, `neoantigen`,
`cancer-genomics`, `healthy-baseline`, `structure`, `comparative-oncology`,
`single-cell`, `functional-assay`, `tooling`

### Controlled `relevance.programs` values
`presentation`, `recognition`, `design`, `comparative`
(the three research programs on /approach, plus comparative-oncology scope)

## Derived fields (added by the build, present only in `index.json`)
- `open_access` — boolean, true for `open`/`registration`
- `agent_automatable` — boolean, true when open **and** an `api`/`download_url` exists
- `ingest_endpoint` — the preferred programmatic entry point
- `feeds_stages` — which research-agenda stages (0–5, see /research) the category feeds
- `commercial_use` — `true` / `false` / `null` (unknown), derived from the license string
- `cross_listed` — `true` when more than one domain pass catalogued the same dataset (set during merge)

## Rules
- Public datasets only. Controlled-access resources (dbGaP/EGA/DUA) are catalogued
  but marked `controlled-access`.
- Be exact on license. Never guess; use `unknown` and explain in `caveats`.
- Prefer primary sources. Verify every URL resolves.
- Flag anything whose terms forbid redistribution or ML training.
