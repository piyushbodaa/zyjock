# Zyjock

A free, independent NEET counselling planning website. All implemented tools are available without payment or an account. Zyjock uses its own interface and branding; it is not affiliated with Zynerd, MCC, NMC, AIIMS or NBEMS. No private Zynerd API or database is used.

## Run locally

From this directory:

```bash
npm run dev
```

Open <http://127.0.0.1:4173>. The command requires Python 3; there are no npm dependencies to install. You can also run `python -m http.server 4173 --bind 127.0.0.1 --directory dist` directly. Serve the `dist/` directory for a static deployment.

## Included tools

- Search and filter colleges, courses, historical cutoffs and seat matrices by exam, state, quota, category, year and round.
- Compare institutions and reported tuition, stipends and service bonds.
- Create, rename, reorder and export choice lists; generate a draft from explicit preferences.
- Inspect available round history and seat changes when comparable records exist.
- Compare an AIR with historical closing ranks; explore explicitly selected demo score-to-rank curves.
- Read source-linked guides, open official notice boards, keep a checklist and export personal reminders to a calendar.
- Import CSV or JSON records, export results, and download or restore a workspace backup. Imports remain marked unverified.

The app does not submit choices to counselling portals. The guidance search is a local reference search, and the notice directory links to official boards rather than claiming a synchronized news feed. There are no push notifications or human counselling services.

## Official data and its limits

The bundled official dataset covers **20 institutions, MBBS, NEET UG, MCC Open Seat Quota, 2025 Round 1**. It contains 200 institution/category pools and 174 opening/closing rank ranges derived from MCC's final allotment result. The 26 pools with zero seats have null ranks.

Every pool's allotment count reconciles with the cited seat matrix after applying MCC's 13 August 2025 removal of one AIIMS New Delhi SC PwD seat: **2,178 seats and 2,178 allotments** in total. Ranks are grouped by **allotted seat category**, not the candidate's personal category. `Open` does not mean only General-category candidates. The matrix's `General-EWS` label is normalized to `EWS`, with the original label retained.

These are historical allotment aggregates, not current vacancies, joined-candidate cutoffs or admission predictions. This is a bounded subset, not national coverage. The public dataset contains no individual candidate records, names, roll numbers or application identifiers.

**Verified fees, stipends, bonds, previous-year seat counts and score-to-rank curves are not bundled.** Unknown numerical values remain `null`; the interface does not treat them as zero. Current rules and deadlines must be checked on the relevant authority's portal.

Eight fictional institutions, each named `Demo · …`, supply 1,440 sample records across NEET UG, NEET PG, NEET MDS, INICET, NEET SS and DNB PDCET. These demonstrate tools for other exams and numerical comparisons. Demo records and curves are explicitly marked and are not admission data. The app starts in the official-data mode; switching exams does not silently substitute demo records.

## Sources and reproduction

The source PDFs are linked from the [MCC UG archive](https://mcc.nic.in/archive-ug/). Exact document URLs, extraction method, corrections and coverage limits are recorded in [data-provenance.txt](data-provenance.txt). The [acquisition summary](sources/acquisition-summary.json) stores only aggregate counts, reconciliation results and source-file SHA-256 hashes.

[sources/build_data.py](sources/build_data.py) builds `dist/data.json`. To reproduce it, download the three official PDFs listed in the provenance file using these local filenames:

- `sources/mcc-2025-ug-r1-inis-seat-matrix.pdf`
- `sources/mcc-2025-ug-r1-result.pdf`
- `sources/mcc-2025-ug-r1-aiims-delhi-seat-removal.pdf`

Then run:

```bash
pdftotext -layout sources/mcc-2025-ug-r1-inis-seat-matrix.pdf sources/mcc-2025-ug-r1-inis-seat-matrix.txt
pdftotext -layout sources/mcc-2025-ug-r1-result.pdf sources/mcc-2025-ug-r1-result.txt
python sources/build_data.py
```

This requires Python 3 and Poppler's `pdftotext`. Original PDFs, extracted text and review images are local acquisition evidence excluded from Git and from the public `dist/` folder. The script and aggregate acquisition summary remain in source control.

## Storage and deployment

Lists, imported records, checklist progress, reminders and read markers are stored in this browser's `localStorage`, keyed by `zyjock.workspace.v1`. They are not synchronized between devices, browsers or origins. Clearing browser storage removes them; use workspace backups to retain a copy. Imports are parsed locally and are not sent to a server.

The application is static HTML, CSS and JavaScript with a bundled JSON dataset. There is no backend account service, payment service or automatic official-data refresh. External authority links open those providers' websites. Deploy only `dist/` and preserve the source and demo labels when extending the dataset.
