# Data contract

## Table grains

| Table | One row represents | Key |
|---|---|---|
| product_source | Projected raw product record | Source row |
| products | Selected valid product identity | Canonical GTIN |
| price_source | Projected raw price observation | Source row |
| prices | Accepted, deduplicated price observation | price_id |
| locations | Latest observed store metadata | location_id |
| notices | Latest version of a food recall notice | notice_id |
| recall_links | Candidate code attached to a notice | notice_id + GTIN |
| recall_rejected | Unparsed identification block | Notice/version + block |
| recall_product_review | Candidate link with description review | notice_id + GTIN |
| catalogue | Product identity and independently aggregated counts | GTIN |
| build_report | Counts, provenance and executed validation gates | One snapshot |

The three source families are independent; normalising one export into multiple tables does not create additional sources. Open Prices already includes denormalised store metadata. It is not advertised as a separately sourced store registry.

## Identifier limits

Length, ASCII digits and the GTIN check digit are validated; all-zero placeholders are rejected. Passing these checks proves structural validity, not that GS1 assigned the code or that a contributor attached it to the correct item. Other plausible-looking placeholders can survive. Source descriptions and original notices remain essential evidence.

## Accepted prices

An accepted observation has a valid product GTIN, a positive price, a currency and an observation date. Repeated price IDs retain one row. Invalid or unlinked source rows remain available in `price_source`. Positive prices in the source can still be wrong; the quality gate does not certify price correctness.

The UI groups a product's monthly medians by currency and `price_per`. It does not convert currency or infer EUR/kg from ambiguous pack sizes. A chart is descriptive, not a claim of a statistically representative price trend.

## Recall matching

Only food-category records are used. The downloaded identification field is a list containing codes, batch text, dates and delimiters. The first token of each pipe-separated block is considered a candidate. It must pass GTIN validation. Remaining blocks are quarantined, not silently treated as products.

Product descriptions are normalised to Latin tokens for a simple disjoint-token flag. Blank descriptions do not generate a false conflict. This intentionally modest heuristic can miss real conflicts and flag legitimate variants. The UI always labels it as a review aid.

The original product/batch block is retained with a link to the authoritative notice. A provided batch number is not automatically confirmed or ruled out. No stock quantity or store inventory data is available.

## CSV outcomes

- `invalid_barcode`: wrong length, characters, check digit or an all-zero placeholder.
- `missing_sku` / `duplicate_sku`: input catalogue identifier needs attention.
- `product_not_in_snapshot`: valid code, no product card in this snapshot.
- `multiple_source_records`: several source rows normalise to the same product code.
- `missing_product_name`: no usable product name.
- `catalogue_name_conflict`: input name and selected product name have no meaningful shared token.
- `recall_description_conflict`: at least one candidate notice has a disjoint description.
- `recall_candidate_check_batch`: historical code relationship requiring original notice and batch review.
- `no_issue_detected`: none of the implemented rules fired; not a safety certificate.

One input row always produces one output row. Issue counts may exceed input rows because several rules can apply to one row. Output fields that could start spreadsheet formulas are escaped before CSV export.

## Update and provenance policy

Raw downloads are immutable within a completed data directory. SHA-256, byte count, source URL and retrieval time are recorded. New snapshots use another directory. Build tables are regenerated, not appended. Product descriptions are current to the downloaded snapshot, not historical reconstructions for every price date.
