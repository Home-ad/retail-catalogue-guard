# Recorded validation

Validated on 20 September 2026 with 64-bit Python 3.12.14 on Windows. Dependency versions are pinned in `requirements-lock.txt`. Sources and SHA-256 values are recorded in [full-build.json](full-build.json).

## Complete data build

| Measure | Count |
|---|---:|
| Downloaded product records | 4,747,229 |
| Rejected product identifiers, including zero placeholders | 192,255 |
| Extra product rows collapsed after canonicalisation | 46 |
| Unique accepted catalogue products | 4,554,928 |
| Downloaded price observations | 314,168 |
| Accepted price observations | 302,866 |
| Observed store locations | 6,639 |
| Downloaded recall records, including non-food categories | 18,648 |
| Latest food notices | 13,748 |
| Accepted notice–code relationships | 12,735 |
| Quarantined recall identification blocks | 6,888 |
| Products with both prices and recall candidates | 1,487 |
| Products with a description-conflict flag | 1,032 |

Quarantined blocks are not necessarily malformed GTINs: they include text or ambiguous identification that the deliberately narrow parser cannot safely interpret. The description heuristic has no measured precision or recall; translations and abbreviations can trigger false positives.

The completed pipeline checks that catalogue grain is preserved and that price and notice counts reconcile to the source relationships after matching. It excludes all-zero codes, which otherwise produce misleading matches despite passing the check-digit calculation.

The working catalogue contains 4,435,398 product-only records, 113,310 with prices but no notice match, 4,733 with notice matches but no prices, and 1,487 with both. This uneven overlap is an explicit limitation, not concealed by the overall row count.

Price observation dates range from 2010-07-08 to 2026-09-19; notice publication dates range from 2021-03-26 to 2026-09-18. Source dates are retained as reported, including unusually old observations. They are not a complete continuous market history.

## Performance observations

The final full build completed in 50.2 seconds, excluding downloads. The 7.89 GB product source is projected to selected columns before DuckDB aggregation. The earlier direct scan with Python scalar callbacks was abandoned after excessive runtime; no unsupported speedup factor is claimed.

A local HTTP review request containing 5,000 distinct real product codes and generated test SKUs completed in 2.518 seconds. All 5,000 rows were retained and matched; 43 required review: 24 missing names and 19 historical recall candidates, of which three also had description conflicts. These are rule outcomes, not independently confirmed defects or affected batches.

Measurements are single local runs, not a benchmark across computers or concurrent users. Peak process memory was not measured. DuckDB has a 2 GB engine memory limit; Arrow and Python also use memory.

## Automated and interface checks

- 25 automated tests pass: identifiers, batch parsing, safe aggregation, repeat builds, input preservation, CSV validation and formula escaping, API errors, source resume guards, and demo round trips.
- Full snapshot build passes product-grain and aggregate-reconciliation assertions.
- Bundled real-data demo loads with checksums verified: 240 products, 7,334 prices, 114 notices and 154 notice–product links.
- Browser checks cover barcode search, product evidence and price chart, loading the 25-product catalogue, downloading its review CSV, uploading duplicate-SKU and invalid-code examples, rejecting malformed headers, and responsive layouts at 1440 × 1050 and 390 × 844.
- Desktop and mobile screenshots were visually inspected. Mobile document width equals viewport width; wide tables use their own scroll container. Normal flows produced no console errors; the deliberately invalid CSV produced the expected HTTP 400 and visible error message.
- A clean Ubuntu GitHub Actions run installed pinned dependencies, passed all 25 tests and loaded and queried the bundled demo: [recorded run](https://github.com/Home-ad/retail-catalogue-guard/actions/runs/35519355845). The test client emits two upstream deprecation warnings; neither affects the passing results.

No paid-client deployment, user adoption, financial savings, semantic-match accuracy, exhaustive browser compatibility or production concurrency testing is claimed. A person must check original notices and batch details before operational decisions.


## Native Power BI follow-up

28 automated tests pass after adding BI export and model checks. The complete seven-table extract has zero duplicate dimension keys and zero orphan fact keys across all six relationships. All observed source categories have English mappings.

The full project was opened, imported, saved and reopened in Power BI Desktop 2.157.1354.0. All three pages were visually inspected. Product search and product/currency/unit selectors were exercised on code 03415581571110: 64 observations, 34 stores and a median of EUR 5.99, matching an independent DuckDB calculation. Initial search on the high-cardinality product slicer can be slow while Power BI builds its search index; the release opens the price page with this example selected.

Twelve native DAX checks in [validation.dax](../powerbi/validation.dax) matched their expected values, including the blank median across mixed products and zero nonblank mixed-product monthly medians. [Count reconciliation screenshot](powerbi-validation.png) and [price checks](powerbi-price-validation.png) record the native results. The native PBIX snapshot and Parquet refresh package are distributed through the release, not as multi-GB raw dumps in Git.

These checks establish import, reconciliation and the exercised interactions. They do not establish semantic-match accuracy, recall completeness, production performance or compatibility with every older Power BI version.
