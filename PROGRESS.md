# Project history

## 20 September 2026 — pipeline and local review workflow

Built the recorded Open Food Facts, Open Prices and RappelConso snapshots into a local Python/DuckDB catalogue. The full build processed 4,747,229 product source records into 4,554,928 unique accepted products, with 302,866 accepted prices and 13,748 food notices. There were 1,487 catalogue products with both price and recall candidates. The build took 50.2 seconds after download; these are results from one development-machine run.

The pipeline validates product identifiers, keeps observation grains separate, reconciles joined totals and replaces the working database only after staging checks pass. The web workflow supports CSV review, evidence drilldown and export. A redistributable demo contains 240 products with source attribution and checksums; full source dumps and generated databases stay outside Git.

Recorded checks: 25 automated tests, Ruff and dependency checks passed; desktop and mobile views were inspected. CSV review/export and demo reload were exercised. A [clean Linux CI run](https://github.com/Home-ad/retail-catalogue-guard/actions/runs/35519355845) installed pinned dependencies, passed the tests and loaded the demo. Details and validation boundaries are in [recorded validation](docs/validation.md) and [full-build.json](docs/full-build.json).

## 20 September 2026 — Power BI and analytical audit

Added a native Power BI report with seven tables, six single-direction relationships, 17 DAX measures and three English pages. Its complete imported model contains 4,582,027 codes: 4,554,928 catalogue products plus evidence for 27,099 codes without a product card. The median guard prevents comparisons across incompatible product, currency and unit selections.

Recorded checks: 28 automated tests and Ruff passed. The full export had no duplicate dimension keys or orphan fact keys. Power BI Desktop import, save, reopen, all three pages and selected filtering interactions were checked; twelve DAX reconciliations matched independent expected values. The cached PBIX and refresh data are distributed in [release v1.1.0](https://github.com/Home-ad/retail-catalogue-guard/releases/tag/v1.1.0); editable definitions are in [powerbi/project](powerbi/project).

The audit measured price coverage of 2.5203% and recall coverage of 0.1366%. A naive join would inflate intersection price observations by 26.47%; separate aggregation avoids that multiplication. These are data-quality and coverage findings, not evidence of business impact. See the [analytical audit](docs/analytical-audit.md).

## 28 September 2026 — documentation review

Reorganised the README around code review, the cached report and the bundled demo; made the demo and full-data paths explicit. Rechecked 28 tests, dependency consistency, demo loading and statistics, CLI CSV export, and the local HTTP demo-review flow. All passed. Documentation link targets were checked. The full source build and native Power BI checks were not repeated; their recorded results above remain dated to 20 September.

## Scope

A portfolio project developed with AI coding assistance, using public data. No paid client deployment, adoption, financial savings or independently validated semantic-match accuracy is claimed. Historical recall applicability requires human batch review; description flags are heuristic, source coverage is uneven and production concurrency is untested. Code and data licensing are documented separately in [LICENSE](LICENSE) and [DATA_LICENSE.md](DATA_LICENSE.md).
