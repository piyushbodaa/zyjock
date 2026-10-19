# Northern and northeastern NEET PG collection

Checked 19 October 2026. Public official sources only. No candidate names, roll numbers, application numbers or personal attributes are retained in `north.json`.

## Reproduction

The document URL register is `document-index.json`. `acquire.py` retrieves the original official PDFs into the ignored `raw/` directory and uses Poppler `pdftotext -layout`. Original links are preserved in each aggregate and financial observation. Additional discovered authority links are in the `*-links.json` registers.

Run `python sources/regions/north/curate.py`, then `uv run --with pymupdf python sources/regions/north/build.py`. The build calls `extensions.py`. PDF geometry is used to aggregate only course/institution/quota/category and rank observations. The source-specific sequential-row and published-total reconciliations are data ingestion safeguards; no app test suite was added or run.

## Rank and seat semantics

- Himachal Pradesh: all five official 2025 final seat-allocation PDFs. Their `Merit No.` is **state merit rank**, not NEET AIR. Every published serial is reconciled, and only group counts/rank endpoints are exported.
- Assam: 2025 round-2 **provisional** select list. Uses `Revised State Rank`; state incentives mean these values cannot be compared with AIR. `NA` (no choice available) rows are excluded. A nonnumeric rank suffix occurs on an NA row and is not rounded or converted into an AIR.
- NEIGRIHMS: 2026 prospectus has 37 total seats: 20 AIQ (already in MCC), 8 open Northeast and 9 institutional roster. Only the 17 non-AIQ seats are added. This is regional institutional counselling, not a Meghalaya-only state quota.
- Tripura: 2025 Annexure C positive pools reconcile to AGMC 46 + TMC 8 + LGBRIMH nomination 1 + IGM NBEMS Diploma 10. LGBRIMH is physically in Assam but its one nomination in this bulletin belongs to Tripura counselling.
- Arunachal: 16 October 2026 official scanned advertisement. Exactly 13 state-quota seats: DNB 1, diploma 1, MD/MS 11. MD/MS category allocation depends on the 200-point roster; no invented category split. The source labels Obstetrics & Gynaecology `MD`, retained verbatim.
- SMIMS: initial 2025 General/Management matrix. Historical initial counts, not current live vacancies. The table's merged fee cells were visually checked before transcription; General Orthopaedics is ₹29.6 lakh, whereas ENT is ₹27 lakh.
- No regional institutions are fuzzily merged into MCC identifiers.

## Financial scopes

- HP government MD/MS: ₹24,000 annual tuition; college total ₹31,500, hostel ₹21,000 and securities separate. The prospectus does not give a nationwide/current stipend or service-bond amount.
- NEIGRIHMS 2026: ₹8,000 annual tuition; annual combined charges ₹28,300. Course-departure penalties vary by year and are not a post-course service bond. Monthly pay referenced without a number stays unknown.
- JNIMS 2025: admission charges ₹50,000 in year 1 and ₹25,000 in years 2/3. Direct/institutional stipend ₹50k/55k/60k by year; in-service stipend explicitly zero. Leaving-course penalty and stipend repayment are separate from post-course service.
- DU 2026: ₹13,000 annual tuition is within ₹19,500 annual university fees; it excludes institution/hostel costs.
- VMMC: ₹15,000 yearly tuition and a ₹3 lakh MD/MS withdrawal penalty. Pay Level 10 basic ₹56,100–177,500 plus allowances is not misrepresented as fixed take-home stipend. Fee/pay document was scanned and read with OCR.
- SMIMS 2025: annual course fees, not merely tuition; the single-instalment quote is stored. Two-instalment total is 4% higher. Hostel/registration/caution separate.
- Zoram Medical College: current official undated disclosure observed on 19 October 2026. PG stipend ₹50k/55k/60k, one-year service bond ₹20 lakh with government-employee exemption. Its separate JR salary and UG internship stipend are not used as PG stipends.
- Uttarakhand: the official PG bond format uploaded February 2025 specifies two years in hilly-region government service and ₹2.5 crore default/course-discontinuation obligation. This form is not asserted to apply to every 2026 entrant; current institution applicability remains to be established.

## Coverage limitations

All 17 assigned jurisdictions have authority/document records. Only jurisdictions with actually extracted numerical records are counted as imported. Punjab archive returned server errors and its indexed prospectus returned 404; Haryana sources timed out. J&K/Ladakh 2026 registration is linked without invented seat counts. Nagaland scholarship notices were not used as PG residency stipends. ZMC's NMC total intake is not a state counselling matrix, and its 2026 MBBS fee document was excluded. Complete state round histories and nationwide fee/stipend/bond coverage remain unfinished.
