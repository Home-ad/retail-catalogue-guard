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

Published at https://github.com/Home-ad/retail-catalogue-guard (PUBLIC). Clean Linux install, 25 tests and demo commands passed in GitHub Actions run 35519355845. Full data is local in ignored data/; the repository includes only the attributed 240-product demo, source code, tests and documentation. CV DOCX/PDF updated outside this repository and visually verified as one A4 page.

The implementation and publication gates are complete. Known limits are documented rather than represented as solved: historical recall applicability requires human batch review, description flags are heuristic, source coverage is uneven, and production concurrency is untested.

## Decisions

- Python and DuckDB for local analytics; FastAPI and a lightweight static frontend for a fully local, free UI.
- Three data source families. Normalized tables are not counted as independent sources.
- Source dumps and generated database stay outside Git. Demo data attribution and ODbL obligations are documented separately from the code license.
- No invented customers, savings, sales, stock levels or completed batch-recall determinations.


## Power BI and analytical audit follow-up — 2026-09-20

Corrected the deliverable emphasis: native Power BI report and full data extract, with the web CSV-review tool retained as a supporting workflow. Seven tables, six single-direction relationships, 17 DAX measures, three English pages. Full imported model: 4,582,027 distinct codes, of which 4,554,928 have catalogue records. Unmatched evidence retained explicitly. The median guard preserves comparable selections across chart dates and locations.

28 automated tests and Ruff pass. Full export has zero duplicate relationship keys and zero orphan fact rows. Native Desktop import, save, reopen, all three pages and product/currency/unit filtering were checked. Twelve DAX reconciliations matched independent expected values. PBIX includes the complete snapshot. Full data assets belong in the v1.1.0 GitHub release; project definitions are in powerbi/project and source-generation commands in powerbi/README.md.

Audit findings: price coverage 2.5203%, recall coverage 0.1366%, only 1,487 three-source catalogue matches; naive join would inflate intersection price observations by 26.47%. Name flags remain heuristic. Missing names total 269,586 including one whitespace-only name. No business impact or semantic precision is claimed. See docs/analytical-audit.md and docs/validation.md.
