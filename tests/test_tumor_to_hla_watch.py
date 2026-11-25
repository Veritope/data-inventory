"""Small recorded-shape fixtures exercise pagination, overlap and revision review offline."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import watch_tumor_to_hla as watch

START = date(2026, 1, 1)
END = date(2026, 1, 7)


def reply(record):
    return json.dumps(record).encode()


def fixture(url):
    """Synthetic metadata, never scientific observations."""
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    if parts.hostname == "www.ebi.ac.uk":
        assert "FIRST_IDATE:[2026-01-01 TO 2026-01-07]" in query["query"][0]
        first = query["cursorMark"] == ["*"]
        row = {"source": "TEST", "id": "001" if first else "002", "title": "Fixture A" if first else "Fixture B"}
        if first:
            row["doi"] = "HTTPS://DOI.ORG/10.0000/FIXTURE"
        return reply({"hitCount": 2, "resultList": {"result": [row]}, "nextCursorMark": "next" if first else None})
    assert parts.hostname == "api.datacite.org"
    assert query["resource-type-id"] == ["dataset"]
    assert "updated:[2026-01-01T00:00:00Z TO 2026-01-07T23:59:59.999Z]" in query["query"][0]
    first = query["page[number]"] == ["1"]
    row = {"id": "10.0000/fixture" if first else "10.0000/dataset",
           "attributes": {"titles": [{"title": "Fixture data"}], "version": "1", "updated": "2026-01-03",
                          "relatedIdentifiers": [{"relatedIdentifier": "10.0000/concept", "relationType": "IsVersionOf"}]}}
    return reply({"meta": {"total": 2}, "data": [row]})


class WatchTest(unittest.TestCase):
    def test_full_scan_and_cross_source_dedup(self):
        out = watch.collect(START, END, fixture)
        self.assertEqual(8, len(out["runs"]))
        self.assertTrue(all(len(run["pages"]) == 2 for run in out["runs"]))
        self.assertEqual(3, len(out["candidates"]))
        one = next(r for r in out["candidates"] if r["id"] == "doi:10.0000/fixture")
        self.assertEqual(4, len(one["stages"]))
        self.assertEqual(2, len(one["records"]))
        self.assertEqual("pending", one["review"])
        with patch.object(watch, "review_index", return_value={(one["id"], one["record_sha256"]): {"decision": "include"}}):
            self.assertEqual("include", next(c for c in watch.collect(START, END, fixture)["candidates"] if c["id"] == one["id"])["review"])
            def revision(url):
                return fixture(url).replace(b'"version": "1"', b'"version": "2"')
            self.assertEqual("pending", next(c for c in watch.collect(START, END, revision)["candidates"] if c["id"] == one["id"])["review"])

    def test_detects_incomplete_or_repeated_pages(self):
        def empty(url):
            return reply({"meta": {"total": 10}, "data": []})
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            watch.pages("datacite", "q", START, END, empty)
        def repeated(url):
            return reply({"hitCount": 4, "resultList": {"result": [{"id": "x", "source": "TEST"}]},
                          "nextCursorMark": "invalid"})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            watch.pages("europepmc", "q", START, END, repeated)

    def test_collection_refs(self):
        records = {r["id"]: r for r in json.loads((watch.ROOT / "index.json").read_text())}
        collection = json.loads((watch.PROJECT / "collection.json").read_text())
        for group in collection["catalog_groups"]:
            for key in group["ids"]:
                self.assertIn(key, records)
        for group in collection["aliases"]:
            landing = records[group["canonical"]]["landing_url"]
            self.assertIn(group["same_deposition"], landing)
            for alias in group["aliases"]:
                self.assertIn(group["same_deposition"], json.dumps(records[alias]))


if __name__ == "__main__":
    unittest.main()
