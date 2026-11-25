#!/usr/bin/env python3
"""Discover publication and data-release metadata. Every output is a review candidate."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "collections" / "tumor-to-hla"
EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
DATACITE = "https://api.datacite.org/dois"
PAGE_SIZE = 100


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def fetch(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "VeritopeEvidenceWatch/1"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            retry_after = error.headers.get("Retry-After", "")
            if retry_after.isdigit() and int(retry_after) > 60:
                raise
            time.sleep(int(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1))
        except (TimeoutError, URLError) as error:
            cause = error.reason if isinstance(error, URLError) else error
            if not isinstance(cause, (TimeoutError, ConnectionResetError)) or attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))


def doi_id(doi):
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", (doi or "").strip(), flags=re.I).lower()
    return f"doi:{doi}" if doi else None


def article(record):
    source, local_id = record["source"], str(record["id"])
    return {
        "id": doi_id(record.get("doi")) or f"epmc:{source}:{local_id}",
        "provider": "europepmc", "provider_id": f"{source}:{local_id}",
        "title": record.get("title"), "published": record.get("firstPublicationDate"),
        "kind": record.get("pubType"), "pmid": record.get("pmid"), "pmcid": record.get("pmcid"),
        "url": f"https://europepmc.org/article/{quote(source, safe='')}/{quote(local_id, safe='')}",
    }


def dataset(record):
    fields = record["attributes"]
    doi = doi_id(record["id"])
    if not doi:
        raise ValueError("DataCite returned a dataset without a DOI")
    return {
        "id": doi, "provider": "datacite", "provider_id": record["id"],
        "title": next((item["title"] for item in fields["titles"] if item.get("title")), None),
        "updated": fields.get("updated"), "created": fields.get("created"),
        "version": fields.get("version"), "publisher": fields.get("publisher"),
        "relations": sorted([
            {"relation": item.get("relationType"), "identifier": item.get("relatedIdentifier")}
            for item in fields.get("relatedIdentifiers", [])
            if item.get("relationType") in ("IsVersionOf", "HasVersion", "IsNewVersionOf", "IsPreviousVersionOf",
                                            "IsSupplementTo", "IsIdenticalTo")
        ], key=encode),
        "url": "https://doi.org/" + doi.removeprefix("doi:"),
    }


def pages(provider, query, start, end, reader):
    cursor = "*"
    seen_cursors = set()
    seen_ids = set()
    page_number = 1
    metadata = []
    records = []
    expected = None
    while True:
        if provider == "europepmc":
            params = {"query": f"({query}) AND FIRST_IDATE:[{start} TO {end}]",
                      "format": "json", "resultType": "lite", "pageSize": PAGE_SIZE, "cursorMark": cursor}
            url = EUROPE_PMC + "?" + urlencode(params)
        else:
            params = {"query": f"({query}) AND updated:[{start}T00:00:00Z TO {end}T23:59:59.999Z]",
                      "resource-type-id": "dataset", "page[size]": PAGE_SIZE, "page[number]": page_number}
            url = DATACITE + "?" + urlencode(params)
        raw = reader(url)
        page = json.loads(raw)
        if provider == "europepmc":
            count = page["hitCount"]
            batch = [article(item) for item in page["resultList"]["result"]]
        else:
            count = page["meta"]["total"]
            batch = [dataset(item) for item in page["data"]]
        if expected is None:
            expected = count
        if count != expected:
            raise ValueError(f"{provider} hit count changed during pagination; rerun with a smaller window")
        for item in batch:
            if item["provider_id"] in seen_ids:
                raise ValueError(f"Duplicate {provider} result across pages; rerun with a smaller window")
            seen_ids.add(item["provider_id"])
        records.extend(batch)
        metadata.append({"url": url, "sha256": digest(raw), "records": len(batch)})
        if len(records) == expected:
            return records, {"provider": provider, "expected_records": expected, "pages": metadata}
        if not batch or len(records) > expected or page_number >= 100:
            raise ValueError(f"Incomplete {provider} results ({len(records)}/{expected}); use smaller date windows")
        if provider == "europepmc":
            seen_cursors.add(cursor)
            cursor = page.get("nextCursorMark")
            if not cursor or cursor in seen_cursors:
                raise ValueError("Europe PMC cursor stalled before hitCount was reached")
        page_number += 1


def review_index():
    entries = json.loads((PROJECT / "decisions.json").read_text())
    index = {}
    for entry in entries:
        key = (entry["id"], entry["record_sha256"])
        if key in index or not re.fullmatch("[a-f0-9]{64}", key[1]):
            raise ValueError(f"Invalid or duplicate review key {key}")
        if entry["decision"] not in {"include", "exclude", "defer"} or not entry["reason"].strip():
            raise ValueError(f"Incomplete review for {key}")
        date.fromisoformat(entry["reviewed_on"])
        if not entry["reviewer"].strip() or (entry["decision"] == "include" and not entry.get("evidence_ref")):
            raise ValueError(f"Missing reviewer or evidence release for {key}")
        index[key] = entry
    return index


def collect(start, end, reader=fetch, report_progress=False):
    config = json.loads((PROJECT / "searches.json").read_text())
    grouped, runs = {}, []
    for search in config["searches"]:
        for provider in ("europepmc", "datacite"):
            if report_progress:
                print(f"Searching {provider} for {search['stage']}...", file=sys.stderr, flush=True)
            items, run = pages(provider, search[provider], start, end, reader)
            runs.append({"stage": search["stage"], **run})
            for item in items:
                group = grouped.setdefault(item["id"], {"stages": set(), "records": {}})
                group["stages"].add(search["stage"])
                source_key = (item["provider"], item["provider_id"])
                if source_key in group["records"] and item != group["records"][source_key]:
                    raise ValueError(f"Metadata changed during scan for {source_key}; rerun discovery")
                group["records"][source_key] = item
    reviews = review_index()
    candidates = []
    for key, group in sorted(grouped.items()):
        records = [record for _, record in sorted(group["records"].items())]
        # Query/stage overlap and harvest dates do not change record identity.
        fingerprint = digest(encode(records))
        decision = reviews.get((key, fingerprint))
        candidates.append({"id": key, "record_sha256": fingerprint, "stages": sorted(group["stages"]),
                           "records": records, "review": decision["decision"] if decision else "pending"})
    return {"schema_version": 1, "interval_utc": {"start": str(start), "end": str(end)},
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "runs": runs,
            "input_sha256": {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in
                             [ROOT / "index.json", PROJECT / "collection.json", PROJECT / "searches.json",
                              PROJECT / "decisions.json", Path(__file__).resolve()]},
            "git_revision": subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip(),
            "candidates": candidates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    parser.add_argument("--end", type=date.fromisoformat, default=yesterday)
    parser.add_argument("--start", type=date.fromisoformat, help="Default: end minus 13 days, inclusive")
    parser.add_argument("--output", type=Path, required=True, help="New JSON file outside the curated registry")
    args = parser.parse_args()
    start = args.start or args.end - timedelta(days=13)
    if start > args.end or args.end > yesterday:
        parser.error("Use an ordered interval of completed UTC dates")
    if args.output.exists():
        parser.error("Choose a new output filename to preserve the previous report")
    report = collect(start, args.end, report_progress=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=args.output.parent, delete=False) as temp:
        temp_path = Path(temp.name)
        try:
            json.dump(report, temp, ensure_ascii=False, sort_keys=True, indent=2)
            temp.write("\n")
            temp.flush()
            os.link(temp_path, args.output)
        finally:
            temp_path.unlink(missing_ok=True)
    pending = sum(item["review"] == "pending" for item in report["candidates"])
    print(f"{len(report['candidates'])} distinct candidates, {pending} pending. {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, URLError, ValueError, KeyError) as exc:
        sys.exit(f"Discovery failed: {exc}. No complete report was saved.")
