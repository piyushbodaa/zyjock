# Contributing to Zyjock (NEET PG)

Thanks for helping keep NEET PG counselling data free and checkable.
Zyjock covers **NEET PG only** — please do not add other exams.

## Run locally

```bash
npm run dev   # python -m http.server 4173 --bind 127.0.0.1 --directory dist
```

Open <http://127.0.0.1:4173>. No npm dependencies; Python 3 only.

## Ground rules

- **Official sources only.** Every seat, cutoff, fee, stipend, bond, and date
  must trace to a dated official publication (MCC, a state counselling
  authority, NMC/NBEMS, or the institution). Keep the source URL and date
  with the record. No scraped aggregator data, no guessed values — unknown
  stays blank, never zero.
- **No candidate PII.** Publish aggregate pools only. Never commit names,
  roll numbers, application IDs, or individual result rows, even if an
  official PDF contains them.
- **No predictions presented as fact.** Historical cutoffs are labelled by
  year and round. Do not add score-to-rank or admission-probability claims
  without a documented, evaluated method.
- **Keep provenance.** Data changes must update
  [data-provenance.txt](data-provenance.txt) (or the relevant file under
  `sources/`) in the same change.

## Rebuild the data

Requires Python 3, [uv](https://docs.astral.sh/uv/), PyMuPDF, and Poppler's
`pdftotext`. Then, in order:

```bash
uv run --with pymupdf python sources/build_pg_history.py
uv run --with pymupdf python sources/build_pg_seats.py
python sources/build_pg_site.py
```

See [README.md](README.md#sources-and-rebuilding) for what each step does.
Source PDFs and extraction caches stay local (they are git-ignored); commit
only scripts, summaries, and the compiled `dist/` JSON.

## Pull requests

- One topic per PR. Say which source document(s) you used.
- For UI changes, note what you tested in the browser.
- By contributing, you agree your contribution is licensed under the
  project's [MIT License](LICENSE) (code) — see [NOTICE.md](NOTICE.md) for
  the code/data split.
