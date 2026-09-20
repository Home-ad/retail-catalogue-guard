# Retail Catalogue Guard

Goal: a public, reproducible retail catalogue review tool using substantial real data from Open Food Facts, Open Prices and RappelConso.

## Completion gates

- Download and process the full food catalogue and the full price and recall snapshots; publish measured counts and source provenance.
- Keep historical barcode candidates separate from confirmed batch applicability. Preserve ambiguous identifiers and product-name conflicts for review.
- Deliver a working CSV catalogue review workflow, source-linked product drilldown, useful charts and downloadable results.
- Run tests for joins, identifiers, missing data, repeat imports, CSV handling and API behavior; inspect the real UI at desktop and mobile widths.
- Include a small redistributable real-data demo, full-data commands, source attribution, limitations and readable modular code.
- Audit staged files and publish a new public GitHub repository. Do not include credentials, personal CV files, raw receipt images or multi-GB dumps.
- Revise CV claims to measured completed behavior only.

## Status

2026-09-20: complete real-data build finished in 50.2 seconds after download. 4,747,229 source product rows become 4,554,928 unique accepted products; 302,866 accepted prices, 13,748 food notices and 1,487 three-source candidates. Checks and provenance are in docs/full-build.json and docs/validation.md.

25 tests pass; Ruff and dependency checks pass. Real CSV review, export, product search and evidence screens work. Desktop and mobile views visually inspected. Demo exported and reloaded with checksums verified. Updated CV stays one A4 page and links to the intended public repository.

Publication and clean GitHub Actions verification are the remaining gates. Full data is local in ignored data/; the repository includes only the attributed 240-product demo, source code, tests and documentation.

## Decisions

- Python and DuckDB for local analytics; FastAPI and a lightweight static frontend for a fully local, free UI.
- Three data source families. Normalized tables are not counted as independent sources.
- Source dumps and generated database stay outside Git. Demo data attribution and ODbL obligations are documented separately from the code license.
- No invented customers, savings, sales, stock levels or completed batch-recall determinations.
