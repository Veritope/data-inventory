# Literature and data watch for the tumor-to-HLA article

The project tracks which human tumors display at least one qualifying altered peptide on classical class I at the time of sampling. This watch finds candidate sources across somatic changes, translation, processing and presentation. A candidate can inform several stages. It becomes evidence only after review of the study and its denominator.

[Source collection](collection.json) · [versioned queries](searches.json) · [decision ledger](decisions.json) · [weekly workflow](../../.github/workflows/tumor-to-hla-watch.yml)

## Run a search

Run from the inventory repository with Python 3.10+ and Git. No third-party Python dependency or API key is needed for discovery.

```sh
python3 scripts/watch_tumor_to_hla.py --output /tmp/hla-watch-new.json
python3 scripts/watch_tumor_to_hla.py --start 2026-11-01 --end 2026-11-15 --output /tmp/hla-watch-backfill.json
python3 -B -m unittest discover -s tests -p 'test_tumor_to_hla_watch.py'
```

The workflow is scheduled for Mondays at 12:17 UTC on the default branch. It searches 14 complete UTC dates through yesterday. The overlap covers one missed week. GitHub's workflow-dispatch inputs allow a backfill after longer gaps. The read-only job writes a downloadable candidate report with 60-day retention. Download and review open candidates before expiry. Unreviewed records stay pending when found again. Record inclusions, exclusions and deferrals in Git. To activate scheduling on a fork, enable Actions and merge the workflow to its default branch.

**Papers.** Europe PMC searches titles and abstracts by first indexing date, with no open-access or journal-only restriction. A newly indexed older publication can appear. Inspect publication type (including preprint, review, correction or retraction) before inclusion. Later title edits and corrections to old records are not comprehensively covered by first-indexed date. At each release recheck included papers' linked corrections, retractions and subsequent journal versions. [Europe PMC search reference](https://europepmc.org/searchsyntax) · [API](https://europepmc.org/RestfulWebService)

**Data.** DataCite searches dataset DOIs by title and metadata-update time. Version and version relations are preserved when present. Titles do not cover every relevant release, and DataCite does not index every repository. Search papers' deposit accessions, linked supplements and official release histories of included cohorts during review. [DataCite REST](https://support.datacite.org/docs/api) · [Query fields](https://support.datacite.org/docs/api-queries)

A run records inclusive dates, full request URLs, result counts, page hashes, retrieval time, Git revision, and hashes of the query file, registry, collection, ledger and collector. The repository can reproduce the exact search definition. Source APIs change over time, so preserve the report to replay its normalized metadata. Paper and dataset versions with different DOIs remain distinct. Equal DOIs across queries/providers are grouped. Papers without a DOI use the provider namespace and accession. Reviewer checks still need to resolve preprint/journal pairs, mirrored deposits, accession aliases and shared patients. Per-record hashes label previously reviewed metadata versions and reopen changed records. Failures or pagination discrepancies give a failed job, never an apparent zero-candidate week.

## Weekly editorial routine

1. Check the last completed report's dates. Backfill gaps, then review records marked `pending` and previously deferred items whose prerequisite has arrived. Read the primary publication, correction status, limitations and data release. Log a reason when a report is peripheral or duplicates an existing source.
2. Identify the data's unit (people, tumors, samples, mutations, peptides, positions, or spectra), denominator, species, histology, assay and exclusions. Map reusable data to existing canonical catalog IDs. Compare accessions and participant overlap against the registry and other papers. For new reusable datasets check access conditions and terms, edit `catalog/*.yaml`, run `python3 scripts/build_index.py`, and inspect all regenerated outputs. Citing a publication is separate from permission to redistribute its data.
3. Save each decision in `decisions.json` using the report's `id` and `record_sha256`, with `decision` (`include`, `exclude`, `defer`), `reason`, `reviewed_on` (YYYY-MM-DD), and `reviewer`. For inclusion record `evidence_ref` as the versioned company-repo evidence commit, file and claim ID. A deferred decision can be amended with history retained by Git. Keep pending items that need longer review in a tracked review branch with the original report entry and fingerprint. Do not store patient records here.
4. Propose changes to the article in `Veritope/veritope/research/projects/tumor-to-hla/`. Pin this inventory repo's commit SHA, catalog ID, primary DOI/accession, resource version, input file hashes and permitted retrieval date. Record study overlap, quality checks, denominator and evidence class. When only an upstream input changes, recalculate its dependent steps under the old model first, then evaluate any model changes separately. Save the before/after estimates with units and uncertainty. Rebuild and smoke-test the article using that release. Link the two review PRs.
5. The approved publication includes a dated change note explaining the source, affected stage, old and new result, and why the difference matters. A week with no eligible changes leaves all released numbers intact. A blocked or incomplete harvest remains outstanding.

## Resuming a partial week

Find the latest successful Actions artifact, then compare its query/revision hashes and interval with the last accepted release. The collector refuses an existing output file. If a provider times out or a moving search changes counts during pagination, rerun to a new file and narrow the date range if necessary. Use `www.ebi.ac.uk` and `api.datacite.org` for read-only HTTPS metadata access. The isolated development environment returned a proxy CONNECT 403 for both on 2026-11-25. Fixture tests exercise both response formats, cross-provider deduplication, changed-version review and partial-page failure. A real zero-result report requires a successful live scan of both providers.
