# National NMC PG stipend disclosures

Official compilation: `https://oldnmc.nmc.org.in/wp-content/themes/twentyfourteen/pdf/Stipend%20Detail%20List.pdf`, document number4730671/2026/UGMEB-NMC. Checked19October2026. The current NMC host returned404; the authority's public legacy host supplied the PDF. Its incomplete certificate chain was handled for this anonymous public download only.

`parse_nmc_stipends.py` parses30PDFpages and reconciles804unique source serials. All804source rows are retained only in the ignored intermediate cache. `financials.json` publishes162rows containing explicit PG wording in the **Stipend of College** column, across22state/UTlabels.119have at least one unambiguous numeric PG amount;43remain unknown. This is a limited public disclosure dataset, not a census of all PG stipends.

The **Stipend of State Govt.** column is retained as raw benchmark evidence but is never assigned as a college payment. UG, internship, SS and senior-resident amounts are not used as PG amounts. A source statement that PG was paid “as mentioned” does not produce a numeric value by copying the adjacent benchmark. Base pay plus unspecified allowance or grade pay is not a total monthly payment and therefore stays null in the comparable monthly field.

Every record keeps its original college stipend cell, benchmark cell, source page, record number and receipt-date string.142reports are dated2024,8are dated2025,12only say“Physical”and retain year:null. These are receipt years, not confirmed academic-year coverage; the2026publication date does not make the payments current. Duplicated institution disclosures are not collapsed into an invented current amount.

Irregular prose numeric-before-PG cells have explicit reviewed overrides in the parser. Year-wise amounts remain arrays with missing years null. One source explicitly says“PG-not paid”; its zero is labelled a historical disclosure, not a current claim. One first-year PG amount is garbled; only its legible second/third year amounts are retained. Generic PG amounts without a study-year label are not copied into all three years.

Rebuild: retain the authority PDF as`sources/national/nmc-stipend.pdf`, then run`uv run --with pymupdf python sources/national/parse_nmc_stipends.py`. Raw PDF/text/cache are ignored; the parser, curated financials and summary are reviewable source artifacts.
