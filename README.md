# Zyjock · NEET PG

A free, independent website for planning **NEET PG counselling**. Every implemented tool is available without payment or an account. Zyjock uses its own interface and branding and is not affiliated with Zynerd, MCC, NMC or NBEMS. No private Zynerd API or database is used.

## Run locally

From this directory:

```bash
npm run dev
```

Open <http://127.0.0.1:4173>. Python 3 is required; there are no npm dependencies to install. The direct command is `python -m http.server 4173 --bind 127.0.0.1 --directory dist`.

Deploy the complete `dist/` directory. Its `data.json` manifest loads active inventory and historical observations from `pg-records-*.json`; zero-seat pools load from `pg-zero-*.json` only when requested. Keep the manifest and both sets of chunks together.

## Included tools

- A personal PG plan with AIR, allotted seat category, specialty, state and tuition preferences.
- College and hospital search, a specialty explorer, and filters for programme, quota, category, source year and round.
- The published 2026 MCC seat matrices beside separately dated, conservatively matched 2025 historical ranks.
- Historical cutoff search and round comparisons, with source links on each observation.
- Institution comparisons, reported financial examples, and a budget calculator using your own assumptions.
- Unlimited choice lists, preference-based draft generation, reordering, CSV export and printing.
- Source-linked PG guidance, official notices and schedules, a checklist, personal reminders and calendar export.
- CSV/JSON import, results export, and workspace backup/restore. Imported records remain labelled unverified.

This release contains NEET PG only, with no fictional institutions or demo ranks. A planning list does not submit or lock choices on an official portal. Guidance search is a local reference search. Notices and schedules are manually checked snapshots, not an automatically synchronized feed; no push notifications or human counselling service is provided.

## Data coverage

| Dataset | Included scope |
|---|---|
| 2026 seat inventory | Four MCC Round 1 matrices published on 15 October 2026: All India, deemed, DNB and central internal quota |
| Published inventory totals | **31,708 seats**, **1,829 MCC institution codes**, and **56,904 category pools**, including 39,513 zero-seat pools |
| 2025 historical results | Final Round 1, Round 2, Round 3 and Stray Vacancy results: **42,921 aggregate pools** from **69,147 allotment events** |

The matrix totals reconcile to their printed documents. Historical extraction reconciles all 106,404 result rows: 69,147 allotment events and 37,257 rows without a current-round allocation, with zero parsing omissions. Events across rounds are not a count of distinct people. Opening and closing AIR are the minimum and maximum rank in the **allotted seat category**, not the candidate's personal category. `Open` includes qualifying candidates from other personal categories.

The curated [institution match artifact](sources/pg-institution-matches.json) links **1,033 institutions one-to-one**: 86 by exact normalized full address and 947 by a unique exact institutional name with the same explicit state. Name matching excludes generic names, ambiguous identities and conflicting explicit postcodes; it uses no fuzzy similarity or abbreviation expansion. A current seat pool receives historical ranks only when the course code, quota and allotted category also match exactly. Historical year and round remain visible. Unmatched pools remain unmatched; this does not mean they are newly created or easier to obtain. The latest build's linked pool counts and publication file inventory are in [sources/pg-site-summary.json](sources/pg-site-summary.json).

**The seat and cutoff dataset covers these MCC sources only.** State counselling outside them is not included. The selected state authority links in the guidance library form a separate directory, not a claim of state dataset coverage. The 2026 matrix is a dated publication snapshot, not live vacancy availability. Historical observations describe allotted seats, not joined admissions or admission guarantees.

Financial coverage is limited to separately sourced institutional examples. Missing tuition, stipend, service-bond and penalty figures remain unknown; a blank field is not zero. Annual tuition, total first-year charges, discontinuation penalties and service bonds are distinct. There is no national fee/stipend/bond database or validated score-to-rank prediction curve bundled with this release.

## Sources and rebuilding

The official starting points are the [MCC PG page](https://mcc.nic.in/pg-medical-counselling/) and [MCC PG archive](https://mcc.nic.in/archive-pg/). [data-provenance.txt](data-provenance.txt) records exact matrix/result URLs, extraction methods, reconciliation and limitations. The separate [PG content provenance](sources/pg-content-provenance.txt) documents the guidance and financial sources.

The published files are ready to serve. To rebuild the data pipeline, use Python 3, [uv](https://docs.astral.sh/uv/), PyMuPDF and Poppler's `pdftotext`. Acquisition scripts download missing official PDFs. Keep the tracked [sources/pg-content.json](sources/pg-content.json) and [sources/pg-institution-matches.json](sources/pg-institution-matches.json) inputs: they supply curated content and the documented institution links, respectively, and are maintained separately from numerical extraction.

Then run, in order:

```bash
uv run --with pymupdf python sources/build_pg_history.py
uv run --with pymupdf python sources/build_pg_seats.py
python sources/build_pg_site.py
```

The history builder creates the official course glossary. The seat builder retains printed institution/course codes and reconciles the four matrices. The site compiler applies the curated institution links and exact course/quota/category matching, keeps current inventory separate from history, and writes the public manifest, active `pg-records-*.json` chunks and lazily loaded `pg-zero-*.json` chunks. It reads acquisition intermediates from `dist/` or ignored `sources/derived/`, curated content from `sources/pg-content.json`, and institution links from `sources/pg-institution-matches.json`. Large acquisition intermediates are moved out of the public directory after compilation. A new source snapshot needs its institution match evidence reviewed before reuse.

Source PDFs, extracted text, raw extraction caches and review images remain local and are excluded from Git and deployment. Public data contains aggregate observations rather than candidate names, roll numbers, application identifiers or individual result rows. Tracked acquisition summaries retain counts, source-file hashes and reconciliation results.

## Browser storage

The PG plan, lists, imported records, checklist, reminders and read markers are saved in this browser's `localStorage` under `zyjock.pg.workspace.v2`. They do not synchronize across browsers, devices or origins. Clearing browser storage removes them; download a workspace backup to keep a copy. Imports are parsed locally and are not sent to a server.

Zyjock is static HTML, CSS and JavaScript. There is no backend account service, payment integration or automatic official-data refresh. External source links open the publishing authority's website. Keep the source dates, unknown values and coverage labels when extending the data.
