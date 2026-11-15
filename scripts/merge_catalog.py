#!/usr/bin/env python3
"""One-time assembler: merge the per-domain research YAML into clean per-category
catalog files.

The data inventory was collected by several agents, each covering a domain and
writing one or more YAML files. The same dataset was often catalogued by more
than one agent (e.g. VDJdb under both the TCR and the single-cell domains). This
script loads all of those files, merges entries that share an `id`, and writes
one file per category into catalog/. After this runs, catalog/ is the source of
truth and build_index.py takes over.

Usage:
    python3 merge_catalog.py <source_dir>   # default: ./_raw next to catalog/
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"

LIST_FIELDS = ["species", "modalities", "formats", "accessions"]

# Same dataset catalogued under two slugs by different passes -> collapse to one.
ID_ALIASES = {
    "abelin-2017-monoallelic-hla1": "abelin-2017-monoallelic",
    "indi-nanobody": "indi",
    "skempi2-xref": "skempi2",
    "tesla-neoantigen-benchmark": "tesla-benchmark",
    "tcia-immunome": "tcia-cancer-immunome-atlas",
    "icdc-tcl01-celllines": "icdc-tcl01",
    "sarkizova-2020-monoallelic-hlathena": "sarkizova-2020-monoallelic",
    "gse238110": "geo-gse238110-canine-osa-rnaseq",
    "prjna742469-sctcr": "canine-sctcr-2024-prjna742469",
    "dla88-monoallelic-atlas": "canine-dla88-immunopeptidome-atlas",
}

VALID_PROGRAMS = {"presentation", "recognition", "design", "comparative"}
PROGRAM_ALIASES = {
    "neoantigen": "presentation", "mhc-binding": "presentation", "binding": "presentation",
    "tcr": "recognition", "tcr-recognition": "recognition",
    "structure": "design", "protein-design": "design",
    "canine": "comparative", "comparative-oncology": "comparative", "veterinary": "comparative",
}
VALID_CATEGORIES = {
    "reference", "mhc-binding", "presentation", "tcr-recognition", "neoantigen",
    "cancer-genomics", "healthy-baseline", "structure", "comparative-oncology",
    "single-cell", "functional-assay", "tooling",
}
CATEGORY_ALIASES = {
    "spatial": "single-cell", "cytometry": "single-cell", "imaging": "tooling",
    "pathology": "comparative-oncology", "epidemiology": "comparative-oncology",
    "antibody": "structure", "immunogenetics": "reference", "clinical": "cancer-genomics",
}
SPECIES_ALIASES = {"canine": "dog", "canis familiaris": "dog", "homo sapiens": "human",
                   "murine": "mouse", "mus musculus": "mouse", "feline": "cat"}


def normalize(e: dict) -> None:
    rel = e.get("relevance")
    if isinstance(rel, dict):
        progs = []
        for p in rel.get("programs", []) or []:
            p = PROGRAM_ALIASES.get(str(p).lower(), str(p).lower())
            if p in VALID_PROGRAMS and p not in progs:
                progs.append(p)
        rel["programs"] = progs or ["presentation"]
    cat = str(e.get("category", "")).lower()
    cat = CATEGORY_ALIASES.get(cat, cat)
    e["category"] = cat if cat in VALID_CATEGORIES else "tooling"
    sp = []
    for s in e.get("species", []) or []:
        s = SPECIES_ALIASES.get(str(s).lower(), str(s).lower())
        if s not in sp:
            sp.append(s)
    e["species"] = sp
    acc = str(e.get("access", "")).lower()
    if acc not in {"open", "registration", "controlled-access", "request"}:
        e["access"] = "controlled-access" if "control" in acc else ("open" if "open" in acc else "request")


def merge_into(dst: dict, src: dict) -> None:
    """Merge src into dst in place; dst was seen first."""
    for k, v in src.items():
        if k == "id":
            continue
        if k not in dst or dst[k] in (None, "", [], {}):
            dst[k] = v
            continue
        if k in LIST_FIELDS and isinstance(dst[k], list) and isinstance(v, list):
            for item in v:
                if item not in dst[k]:
                    dst[k].append(item)
        elif k == "relevance" and isinstance(dst[k], dict) and isinstance(v, dict):
            dprog = dst[k].setdefault("programs", [])
            for p in v.get("programs", []) or []:
                if p not in dprog:
                    dprog.append(p)
            if len(str(v.get("why", ""))) > len(str(dst[k].get("why", ""))):
                dst[k]["why"] = v["why"]
        elif k == "provenance" and isinstance(dst[k], dict) and isinstance(v, dict):
            drefs = dst[k].setdefault("key_refs", [])
            for r in v.get("key_refs", []) or []:
                if r not in drefs:
                    drefs.append(r)
            if not dst[k].get("maintainer") and v.get("maintainer"):
                dst[k]["maintainer"] = v["maintainer"]
        elif isinstance(v, str) and isinstance(dst[k], str):
            # keep the more informative string (longer), but never clobber with empty
            if len(v) > len(dst[k]):
                dst[k] = v
        # else: keep dst's value (first wins)
    # track that this id came from multiple source files
    dst.setdefault("_merged_from", [dst.get("_source_file", "?")])
    sf = src.get("_source_file")
    if sf and sf not in dst["_merged_from"]:
        dst["_merged_from"].append(sf)


def main() -> int:
    src_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_raw"
    files = sorted(src_dir.glob("domain-*.yaml"))
    if not files:
        sys.exit(f"no domain-*.yaml in {src_dir}")

    by_id: dict[str, dict] = {}
    order: list[str] = []
    merged_count = 0
    raw = 0
    for f in files:
        data = yaml.safe_load(f.read_text()) or []
        for e in data:
            raw += 1
            e["_source_file"] = f.name
            if e.get("id") in ID_ALIASES:
                e["id"] = ID_ALIASES[e["id"]]
            normalize(e)
            eid = e.get("id")
            if not eid:
                print(f"skip: entry with no id in {f.name}", file=sys.stderr)
                continue
            if eid in by_id:
                merge_into(by_id[eid], e)
                merged_count += 1
            else:
                by_id[eid] = e
                order.append(eid)

    # strip internal bookkeeping before writing
    for e in by_id.values():
        e.pop("_source_file", None)
        mf = e.pop("_merged_from", None)
        if mf and len(mf) > 1:
            e["cross_listed"] = True  # flag: catalogued by >1 domain agent

    # split by category
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for eid in order:
        e = by_id[eid]
        by_cat[e.get("category", "uncategorized")].append(e)

    CATALOG.mkdir(exist_ok=True)
    for cat, entries in sorted(by_cat.items()):
        entries.sort(key=lambda x: x["id"])
        out = CATALOG / f"{cat}.yaml"
        out.write_text(yaml.safe_dump(entries, sort_keys=False, allow_unicode=True,
                                      default_flow_style=False, width=100))
    print(f"raw entries: {raw}")
    print(f"merged duplicates: {merged_count}")
    print(f"unique datasets: {len(by_id)}")
    print("by category:")
    for cat, entries in sorted(by_cat.items()):
        print(f"  {cat}: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
