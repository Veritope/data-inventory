# Veritope data inventory

An open, versioned catalog of the public datasets relevant to Veritope's work:
tumor-antigen **presentation**, T-cell **recognition**, protein **design**, and
the **comparative-oncology** (dog → human) setting we start in. This is Stage 0 of
the [research agenda](https://veritope.com/research/): map the data before making
modeling claims.

It is built to be used, not just read — by our pipelines, by collaborators, and by
automated agents. See [`AGENTS.md`](AGENTS.md) for programmatic use.

## Layout
```
data-inventory/
  catalog/          hand-curated YAML, one list item per dataset  ← source of truth
  SCHEMA.md         the entry schema and controlled vocabularies
  AGENTS.md         how an agent/pipeline should consume this
  scripts/
    build_index.py  validates the catalog and regenerates the files below
  index.json        flat, normalized index of every dataset (load this)
  index.csv         spreadsheet view
  stats.json        counts by category / program / access / species
  by-category.md    grouped human-readable view
  by-program.md     grouped by Veritope program
```
`index.json`, `index.csv`, `stats.json`, and the `by-*.md` files are **generated**.
Edit the YAML in `catalog/`, then run the build.

## How datasets are organized
Each dataset is tagged by:
- **category** — what kind of data it is (presentation, tcr-recognition,
  cancer-genomics, healthy-baseline, structure, comparative-oncology, …)
- **program** — which Veritope program it serves (presentation / recognition /
  design / comparative)
- **access** — `open`, `registration`, `controlled-access`, or `request`
- **species**, **license**, and ingestion metadata (endpoint, automatability)

The build derives, for each entry, whether an agent can pull it today
(`agent_automatable`), the preferred `ingest_endpoint`, and which research stages
it feeds. This is the "process on ingest" layer: a pipeline can filter the inventory
without re-reading every source.

## Build
```bash
python3 scripts/build_index.py
```
Validation fails loudly (non-zero exit) on a missing required field, an unknown
category, or a duplicate id, so the generated indexes never drift from the schema.

## Scope and honesty
- **Public data only.** Controlled-access resources are listed and marked; we do not
  work around access controls.
- **Licenses are recorded exactly.** Anything that forbids redistribution or ML use
  is flagged in `caveats`. Respect it.
- Canine presentation, TCR, and DLA (dog MHC) data are **sparse**. The catalog
  documents what exists and, just as importantly, where the gaps are — that gap is
  part of what we work on.
- Nothing here is a medical claim. This is a research resource.

## Snapshot

_Generated from the catalog; see [`stats.json`](stats.json) for the live numbers._

- **344 datasets** across 12 categories.
- **303 open and agent-automatable** (open license/access **and** a programmatic endpoint).
- **Access:** 291 open · 35 controlled-access (DUA/dbGaP/EGA) · 12 registration · 6 by request.
- **Commercial use:** 116 clearly OK · 21 restricted (non-commercial / separate licence) · 207 unverified (treat as "check before commercial use").
- **Species:** 274 human · 99 mouse · **82 dog** · 87 other/multi.
- **By program:** presentation 187 · recognition 139 · design 211 · comparative 136 (a dataset can serve several).

### Data volume
Only 20 datasets publish a download size; the rest (including the large
controlled-access genomics cohorts) do not state one, so these are lower bounds.

- **Measured total: ~9.8 PB** — but **99.7% is EMPIAR** alone (raw cryo-EM images,
  catalogued for the sequence→structure work).
- **Excluding EMPIAR: ~27 TB** of published sizes, led by AlphaFold DB (~21 TB),
  mdCATH (~3.3 TB), and the HLA Ligand Atlas immunopeptidome deposits (~2.1 TB).
- Full per-dataset sizes are in `index.json` (`size_bytes`).

### Known gaps (the canine problem, documented)
- Canine immunopeptidome data is **DLA-88-only**; no other class I locus and no
  class II at scale. The richest release is PXD074485 (dog + human MHC-I).
- **No epitope-labelled canine TCRs** (no VDJdb/McPAS equivalent) and no
  IMGT-grade canine germline V/D/J.
- No DLA breed allele-frequency resource.

These gaps are the point: they are where Veritope's own data generation adds the
most.
