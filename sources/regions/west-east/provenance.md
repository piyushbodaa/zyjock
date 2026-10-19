# Western, central and eastern NEET PG acquisition

Checked 19 October 2026. Sources are public state counselling authorities, government departments and institutional notices. This is explicitly partial coverage; absence of an amount is not zero.

`west-east.json` provides eleven jurisdiction registers, source institute identities, aggregate historical cutoff/seat observations, scoped financial facts and reconciliation counts. It contains no candidate names, identifiers, dates of birth or application numbers.

## Rebuild

- Run `python sources/regions/west-east/acquire.py` for the initial source batch. The full observed URL manifest is `downloads.json`; additional public documents were acquired from those URLs. Raw PDFs, text, renderings and caches are ignored.
- Use Poppler `pdftotext -layout` on PDFs to create matching `.txt` filenames in `raw/`.
- Use `uv run --with pymupdf python sources/regions/west-east/extract_tables.py` for initial tables.
- The extractor also handles Goa, Jharkhand and Chhattisgarh through PyMuPDF `page.find_tables().extract()` in page order.
- Run `uv run --with pymupdf python sources/regions/west-east/extract_maharashtra.py`. This reads table columns geometrically and discards personal fields before storing intermediate rows.
- Run `python sources/regions/west-east/build.py` to publish only aggregates.

## Interpretation

- Gujarat cutoff records use explicit NEET AIR. Empty AIR cells are not filled from state merit. Compiled last rank has no invented round assignment. Gujarat seat records contain GQ/MQ/NRI columns only; the AIQ column is excluded to prevent duplicating MCC inventory.
- MP records use AIR and retain the original allotted category, institutional preference and MP-MBBS eligibility split. Source “institute code” is a program code and is not used as a college identifier.
- Bihar uses NEET opening/closing ranks. The separate UR/category state ranks are not used.
- Maharashtra uses SML only, not AIR. Source selections are provisional. Its course and institution labels are abbreviated by the publisher and preserved. No fuzzy join to MCC institutes is performed.
- Jharkhand uses round-specific CML state merit ranks. These must not be compared with AIR or with another round's reconstituted CML list. Only current allotment columns are aggregated.
- Goa 2026 category totals reconcile to 72 seats; PwD counts are split out of their inclusive categories without double counting.
- Chhattisgarh uses the revised combined Round 1+2 list issued after cancellation of earlier rounds. All 262 numbered allocations are parsed. The separate mop-up matrix is explicitly a historical vacancy snapshot, not live availability or total capacity.

## Financial review

- Annual tuition, stipend, service obligation, discontinuation penalty and refundable deposits remain distinct.
- West Bengal's scanned fee order was OCR-assisted and visually reviewed on both pages. Its six institutions produce sixteen quota/clinical-scope annual fee entries.
- Chhattisgarh's official interim fee order expressly covers 2024-25, 2025-26 and 2026-27; six institution/course scopes retain the interim qualification.
- NAMO's twelve annual tuition rates come from its institutional schedule. Other charges and refundable security are separate.
- Odisha government tuition is ₹35,000 per annum; ₹10 lakh plus stipend/salary recovery is discontinuation, not service-bond buyout.
- Goa's 2026 rules state a one-year conditional service obligation. Their fee clause refers to 2025-26 per-term fees; no 2026 annual total is inferred. Its numeric stipend disclosure is FY 2023-24, clearly historical.
- GMC Nagpur's official indexed 2025-26 proforma supports its fee and one-year/₹50 lakh service bond; direct acquisition returned HTTP444, but the official PDF text and pages were available through web indexing.
- BJMC's official indexed joining notice distinguishes ₹30,000 first-year government fee from ₹100,800 refundable caution (one month stipend), with six explicit bond-exempt specialties. Its direct PDF currently returned404. The Gujarat general table combines ₹130,800 under tuition, so that figure is not imported as an annual tuition value.

## Acquisition gaps

Rajasthan source downloads returned503 and its indexed generic static booklet contained2024 information. No2025 financial or eligibility facts were invented from it. Other states retain explicit per-state coverage notes. State financial policies are not automatically applied to every college.
