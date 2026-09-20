# Analytical audit and project purpose

## The actual question

How much external evidence can be linked to a product catalogue, which records need manual review, and where do the sources fail to agree or provide enough information?

The intended user is a retail data or catalogue operations analyst. Given a supplier spreadsheet, they need to check product identifiers and descriptions, find historical recall candidates, and retain evidence for a colleague to inspect. Price observations provide secondary context. They do not establish stock, sales, margin or supplier cost.

This is a data quality and historical traceability project. It is not a food-safety risk score, a complete European recall register, a recall prediction model or proof that current stock must be removed. No real customer adoption or time saving has been measured.

## What the second review found

1. **The first deliverable missed the BI emphasis.** A working web tool demonstrates application development, but it does not demonstrate Power BI modelling. The new native project includes separate dimensions, facts, relationships, Power Query imports and DAX measures.
2. **Volume is real; joint coverage is limited.** There are 4,554,928 accepted catalogue products. Only 114,797 have prices (2.5203%); 6,220 have recall candidates (0.1366%); 1,487 have both. The global product catalogue and French notice register have different geographic scope. These percentages are source matching coverage, not population risk estimates.
3. **Unmatched evidence matters.** 31,597 accepted price observations do not match a catalogue product. Across prices and recall links, 27,099 distinct codes have no product card. The BI product dimension retains these codes with `InProductCatalogue = false`, rather than dropping observations or pretending those codes have complete product records. Evidence flags are calculated from the price and notice tables even for codes without a catalogue card.
4. **A naive join inflates counts.** In the three-source intersection there are 5,271 price observations and 1,897 notice–code links. A direct product–price–recall join produces 6,666 rows. Counting those rows as observations would overstate the price count by 26.47%. The pipeline aggregates independently; the BI model has no fact-to-fact relationship.
5. **Name differences are not confirmed identity conflicts.** The lexical rule also flags translations and abbreviations. UI labels now say “needs review”. The 1,032 catalogue flags are not 1,032 independently verified mistakes. No precision/recall estimate is available.
6. **The presentation was not consistently English.** Category charts now use an explicit 24-entry English mapping, retaining the source category separately. Raw names, reasons and batch descriptions stay in the original language. Inventing English source text would weaken traceability.
7. **Check digits do not establish identity.** Zero-only codes are excluded. Other structurally valid but unassigned or misused identifiers can survive. The project does not claim GS1 registry verification.

## What was checked

The actual full database was queried, not just the 240-product demo. Notice IDs and source notice numbers are unique across all 13,748 food records; no duplicated notice-number versions were found in this snapshot. No empty accepted currency values or non-finite accepted prices were found. One whitespace-only name was found; BI treats it as a missing name, giving 269,586 missing names (269,585 empty strings plus one whitespace-only value).

All six exported BI relationships are checked for duplicate dimension keys and unmatched fact keys. They pass with zero violations. Both date dimensions are continuous and separate: one for price observation dates, another for notice publication dates. All 24 observed categories have English labels. The full seven-table BI extract contains 4,582,027 product-code dimension rows, including the 27,099 missing-card records; this is not advertised as 4,582,027 complete product records.

## The difficult manual work

A person would need to preserve leading zeros, distinguish GTINs from lot numbers and dates, resolve duplicate source records, recognise missing product cards, and inspect the original notice before deciding whether a batch applies. When joining tables, they must keep a price observation distinct from a notice and from a notice–product link. These are repeatable data-preparation and modelling problems the implementation tackles. The final judgement about a real batch still belongs to a person.

## Remaining limits

Matching accuracy has not been independently labelled or measured. Recall parser completeness, operational adoption, causal claims, avoided harm, savings and production concurrency are not established. Prices mix stores, discounts and changing product metadata; the DAX median is therefore blank unless one product code, one currency and one reported unit are selected. Even that guard does not establish historical packaging equivalence.

Method references: [Microsoft star schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema), [Power Query local Parquet import](https://learn.microsoft.com/en-us/power-query/connectors/parquet), [Power BI project semantic models](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset).
