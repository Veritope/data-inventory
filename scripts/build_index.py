#!/usr/bin/env python3
"""Build the Veritope data inventory indexes from the hand-curated catalog.

Reads every YAML file in research/data-inventory/catalog/, validates each entry
against the schema, normalizes and enriches it, then writes machine-readable
indexes that downstream pipelines and agents consume:

  index.json   flat list of all datasets, with derived ingestion fields
  index.csv    spreadsheet view of the same
  stats.json   counts by category / program / access / species
  by-program.md, by-category.md   grouped human-readable views

Run from anywhere:  python3 research/data-inventory/scripts/build_index.py
Exit code is non-zero if any entry fails validation, so CI can gate on it.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"

REQUIRED = [
    "id", "name", "category", "species", "description",
    "landing_url", "license", "access", "relevance",
]

CATEGORIES = {
    "reference", "mhc-binding", "presentation", "tcr-recognition",
    "neoantigen", "cancer-genomics", "healthy-baseline", "structure",
    "comparative-oncology", "single-cell", "functional-assay", "tooling",
}

PROGRAMS = {"presentation", "recognition", "design", "comparative"}

# Which research-agenda stage(s) each category primarily feeds (see /research).
CATEGORY_STAGES = {
    "reference": [0],
    "tooling": [0],
    "mhc-binding": [0, 1, 2],
    "presentation": [0, 1, 2, 3],
    "tcr-recognition": [0, 1, 2, 3],
    "neoantigen": [0, 2, 4],
    "cancer-genomics": [0, 2, 3],
    "healthy-baseline": [0, 2],
    "structure": [0, 1, 5],
    "comparative-oncology": [0, 2, 3, 4, 5],
    "single-cell": [0, 2, 3],
    "functional-assay": [1, 2, 3],
}

OPEN_ACCESS = {"open", "registration"}

# License substrings that signal a restriction on commercial use. Conservative:
# anything matching flips commercial_use to False so a for-profit double-checks.
NONCOMMERCIAL_MARKERS = ("-nc", " nc", "non-commercial", "noncommercial",
                         "academic", "research use only", "research-only")
# Licenses we treat as clearly commercial-safe when matched exactly-ish.
PERMISSIVE_MARKERS = ("cc0", "cc by 4.0", "cc-by-4.0", "cc by 3.0", "mit",
                      "apache", "bsd", "public domain", "odc-by", "cc by-sa")


def commercial_use(license_str: str) -> object:
    """True = commercial-safe, False = restricted, None = unknown/verify."""
    s = (license_str or "").strip().lower()
    if not s or s == "unknown" or s == "custom":
        return None
    if any(m in s for m in NONCOMMERCIAL_MARKERS):
        return False
    if "-nd" in s or "noderiv" in s:
        return None  # NoDerivs: verbatim ok, but modified redistribution needs permission
    if any(m in s for m in PERMISSIVE_MARKERS):
        return True
    return None


def _human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} EB"


def load_entries() -> list[dict]:
    entries: list[dict] = []
    files = sorted(CATALOG.glob("*.yaml")) + sorted(CATALOG.glob("*.yml"))
    for f in files:
        data = yaml.safe_load(f.read_text()) or []
        if not isinstance(data, list):
            sys.exit(f"{f.name}: top level must be a YAML list")
        for e in data:
            e["_source_file"] = f.name
            entries.append(e)
    return entries


def validate(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for e in entries:
        where = f"{e.get('_source_file', '?')}:{e.get('id', '<no id>')}"
        for field in REQUIRED:
            if not e.get(field):
                errors.append(f"{where}: missing required field '{field}'")
        cat = e.get("category")
        if cat and cat not in CATEGORIES:
            errors.append(f"{where}: unknown category '{cat}'")
        eid = e.get("id")
        if eid:
            if eid in seen:
                errors.append(f"{where}: duplicate id (also in {seen[eid]})")
            else:
                seen[eid] = where
        rel = e.get("relevance") or {}
        for p in rel.get("programs", []) or []:
            if p not in PROGRAMS:
                errors.append(f"{where}: unknown program '{p}'")
    return errors


def enrich(e: dict) -> dict:
    """Add derived fields that make the entry usable without re-reading the source."""
    access = (e.get("access") or "").strip().lower()
    has_endpoint = bool(e.get("api") or e.get("download_url"))
    # Can an automated agent pull this without a human in the loop?
    e["agent_automatable"] = access in OPEN_ACCESS and has_endpoint
    e["open_access"] = access in OPEN_ACCESS
    e["feeds_stages"] = CATEGORY_STAGES.get(e.get("category"), [])
    # Preferred programmatic entry point for ingestion.
    e["ingest_endpoint"] = e.get("api") or e.get("download_url") or e.get("landing_url")
    e["commercial_use"] = commercial_use(e.get("license"))
    e.pop("_source_file", None)
    return e


def write_outputs(entries: list[dict]) -> None:
    entries = [enrich(e) for e in entries]
    entries.sort(key=lambda e: (e["category"], e["id"]))

    # index.json
    (ROOT / "index.json").write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")

    # index.csv (flattened scalar view)
    cols = [
        "id", "name", "category", "species", "access", "open_access",
        "agent_automatable", "commercial_use", "license", "landing_url",
        "ingest_endpoint", "feeds_stages", "scale",
    ]
    with (ROOT / "index.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for e in entries:
            row = []
            for c in cols:
                v = e.get(c, "")
                if isinstance(v, list):
                    v = "; ".join(str(x) for x in v)
                row.append(v)
            w.writerow(row)

    # stats.json
    sized = [e for e in entries if isinstance(e.get("size_bytes"), (int, float)) and e["size_bytes"] > 0]
    total_bytes = int(sum(e["size_bytes"] for e in sized))
    stats = {
        "total": len(entries),
        "agent_automatable": sum(e["agent_automatable"] for e in entries),
        "open_access": sum(e["open_access"] for e in entries),
        "commercial_use_ok": sum(1 for e in entries if e["commercial_use"] is True),
        "commercial_use_restricted": sum(1 for e in entries if e["commercial_use"] is False),
        "commercial_use_unknown": sum(1 for e in entries if e["commercial_use"] is None),
        "total_size_bytes": total_bytes,
        "total_size_human": _human_bytes(total_bytes),
        "entries_with_known_size": len(sized),
        "entries_with_unknown_size": len(entries) - len(sized),
        "by_category": dict(Counter(e["category"] for e in entries)),
        "by_access": dict(Counter(e.get("access") for e in entries)),
        "by_program": dict(Counter(
            p for e in entries for p in (e.get("relevance") or {}).get("programs", []) or []
        )),
        "species": dict(Counter(
            s for e in entries for s in (e.get("species") or [])
        )),
    }
    (ROOT / "stats.json").write_text(json.dumps(stats, indent=2) + "\n")

    _grouped_md(entries, "category", ROOT / "by-category.md", "Datasets by category")
    _grouped_program_md(entries, ROOT / "by-program.md")
    return stats


def _row(e: dict) -> str:
    tags = []
    if e["agent_automatable"]:
        tags.append("auto")
    elif e["open_access"]:
        tags.append("open")
    else:
        tags.append(e.get("access", "?"))
    tag = ", ".join(tags)
    return f"- **[{e['name']}]({e['landing_url']})** — {e.get('license','?')} · {tag}. {e.get('description','').strip().splitlines()[0] if e.get('description') else ''}"


def _grouped_md(entries, key, path, title):
    groups = defaultdict(list)
    for e in entries:
        groups[e[key]].append(e)
    lines = [f"# {title}", "", "_Generated by scripts/build_index.py — do not edit by hand._", ""]
    for g in sorted(groups):
        lines.append(f"## {g} ({len(groups[g])})")
        lines.append("")
        for e in sorted(groups[g], key=lambda x: x["id"]):
            lines.append(_row(e))
        lines.append("")
    path.write_text("\n".join(lines))


def _grouped_program_md(entries, path):
    groups = defaultdict(list)
    for e in entries:
        for p in (e.get("relevance") or {}).get("programs", []) or ["(unassigned)"]:
            groups[p].append(e)
    lines = ["# Datasets by Veritope program", "",
             "_Generated by scripts/build_index.py — do not edit by hand._", ""]
    for g in sorted(groups):
        lines.append(f"## {g} ({len(groups[g])})")
        lines.append("")
        for e in sorted(groups[g], key=lambda x: (x["category"], x["id"])):
            lines.append(_row(e))
        lines.append("")
    path.write_text("\n".join(lines))


def main() -> int:
    if not CATALOG.exists():
        sys.exit(f"no catalog dir at {CATALOG}")
    entries = load_entries()
    if not entries:
        print("warning: no entries found")
    errors = validate(entries)
    if errors:
        print(f"VALIDATION FAILED ({len(errors)} errors):", file=sys.stderr)
        for err in errors:
            print("  " + err, file=sys.stderr)
        return 1
    stats = write_outputs(entries)
    print(f"OK: {stats['total']} datasets "
          f"({stats['agent_automatable']} agent-automatable, "
          f"{stats['open_access']} open, "
          f"{stats['commercial_use_ok']} commercial-OK). "
          f"Known data volume: {stats['total_size_human']} across "
          f"{stats['entries_with_known_size']} datasets "
          f"({stats['entries_with_unknown_size']} size unknown). "
          f"Wrote index.json, index.csv, stats.json, by-category.md, by-program.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
