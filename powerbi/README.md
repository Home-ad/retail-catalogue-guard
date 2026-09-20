# Retail Catalogue Guard in Power BI

The native Power BI project uses the actual prepared source records. The web application remains an optional operational CSV-review interface.

## Ready-to-open full snapshot

Download `Retail.Catalogue.Guard.pbix` from [release v1.1.0](https://github.com/Home-ad/retail-catalogue-guard/releases/tag/v1.1.0). The data is imported inside the file: open it in Power BI Desktop without running Python. Three English pages are included. The price page is saved with a documented real product selected; other pages retain their full-snapshot context.

For refresh or editable project files, download and extract `Retail.Catalogue.Guard.PowerBI.zip`. Set the `DataFolder` parameter in **Transform data > Edit parameters** to the extracted `data` directory before refreshing. The release PBIP expects `C:/RetailCatalogueGuard/data`; the saved PBIX retains the author's original extract path. Set the parameter to your extracted data folder when refreshing on another computer. The cached PBIX does not need refresh merely to view it. Use a recent Power BI Desktop version; validation used 2.157.1354.0.

No paid service is required for local viewing or refresh. Internet sharing through Microsoft's service is a separate option and is not part of this delivery.

## Build the full project locally

After the main README's installation and full dataset build:

```sh
catalogue-guard powerbi --output output/powerbi-full
```

Open `output/powerbi-full/Retail Catalogue Guard.pbip` in Power BI Desktop and select Refresh. The generator sets the local data-folder parameter, creates seven Parquet tables, a semantic model, 17 DAX measures and three report pages. A PBIP includes the report and model definitions; its first open requires importing the accompanying Parquet data.

For the small real-data demo:

```sh
catalogue-guard --data-dir data-demo demo
catalogue-guard --data-dir data-demo powerbi --output output/powerbi-demo
```

All labels and measures are English. Columns ending in `Original` preserve source text. Categories are translated using an explicit mapping, not by changing the source notices.

## Model

| One side | Many side | Filter direction |
|---|---|---|
| DimProduct.ProductCode | FactPrice.ProductCode | Single |
| DimProduct.ProductCode | FactRecallLink.ProductCode | Single |
| DimLocation.LocationId | FactPrice.LocationId | Single |
| DimPriceDate.Date | FactPrice.ObservedDate | Single |
| DimRecallDate.Date | DimNotice.PublishedDate | Single |
| DimNotice.NoticeId | FactRecallLink.NoticeId | Single |

No direct fact-to-fact relationship and no automatic bidirectional filtering. Product-only codes and evidence without a product card are retained; `InProductCatalogue` distinguishes them. The unknown location uses key -1. Identifiers stay text. Numeric identifier columns are not summed.

## Report pages

1. **Catalogue coverage:** accepted product count, price coverage, recall coverage, missing names and overlap. These are coverage diagnostics, not safety ratings.
2. **Historical recall evidence:** category and publication history, counts of notices and candidate links. Multiple product codes on one notice must not multiply the notice count.
3. **Price observations:** product, currency and reported unit selectors; monthly median and geographic observation coverage. The median is deliberately blank across incompatible selections.

Try product code `03415581571110`, currency `EUR`, unit `Unspecified`. It has 64 observations in the full snapshot. A price trend is descriptive; no sales, demand or savings are inferred.

See [the analytical audit](../docs/analytical-audit.md) for the business purpose, actual weaknesses and validation boundaries. Data files and any exported PBIX retain the data licensing terms in [DATA_LICENSE.md](../DATA_LICENSE.md).

The product selector has search enabled in the saved release; its first search across millions of codes can be slow. For regenerated projects, use the slicer ellipsis > Search if needed. The twelve-check `validation.dax` query is specific to the recorded full snapshot, not the demo or future source snapshots.
