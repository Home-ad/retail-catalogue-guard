import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .download import sha256
from .labels import CATEGORY_EN
from .pipeline import connect

QUERIES = {
    "DimProduct": """
        WITH codes AS (
            SELECT gtin FROM catalogue UNION SELECT gtin FROM prices UNION SELECT gtin FROM recall_links
        ), price_codes AS (SELECT DISTINCT gtin FROM prices),
        recall_codes AS (SELECT DISTINCT gtin FROM recall_links)
        SELECT k.gtin AS ProductCode, c.gtin IS NOT NULL AS InProductCatalogue,
            coalesce(nullif(trim(c.name),''),'[No source name]') AS ProductNameOriginal,
            coalesce(nullif(trim(c.brand),''),'[Unknown brand]') AS Brand,
            coalesce(c.quantity,'[Unknown pack size]') AS PackSizeOriginal,
            coalesce(c.source_rows,0)::BIGINT AS SourceRows,
            c.gtin IS NOT NULL AND coalesce(trim(c.name),'')='' AS MissingName,
            p.gtin IS NOT NULL AS HasObservedPrice,
            r.gtin IS NOT NULL AS HasRecallCandidate,
            coalesce(c.name_conflict,false) AS DescriptionReviewFlag,
            CASE WHEN c.gtin IS NULL THEN 'No product record'
                 WHEN c.price_count>0 AND c.notice_count>0 THEN 'Prices and recall candidates'
                 WHEN c.price_count>0 THEN 'Prices only'
                 WHEN c.notice_count>0 THEN 'Recall candidates only'
                 ELSE 'Product record only' END AS CoverageGroup
        FROM codes k LEFT JOIN catalogue c USING(gtin) LEFT JOIN price_codes p USING(gtin) LEFT JOIN recall_codes r USING(gtin)
    """,
    "FactPrice": """
        SELECT price_id::BIGINT AS PriceId, gtin AS ProductCode,
            observed_on::DATE AS ObservedDate, price::DOUBLE AS ObservedPrice,
            currency AS Currency, coalesce(price_per,'Unspecified') AS PriceUnit,
            coalesce(location_id,-1)::BIGINT AS LocationId, discounted AS IsDiscounted,
            'https://prices.openfoodfacts.org/prices/' || price_id AS SourceURL
        FROM prices
    """,
    "DimLocation": """
        SELECT location_id::BIGINT AS LocationId, upper(coalesce(country,'Unknown')) AS CountryCode,
            coalesce(city,'Unknown') AS City, coalesce(store,'Unknown') AS StoreOriginal
        FROM locations
        UNION ALL SELECT -1, 'Unknown', 'Unknown', 'Unknown'
    """,
    "DimNotice": """
        SELECT n.notice_id::VARCHAR AS NoticeId, n.published_at::DATE AS PublishedDate,
            coalesce(m.english,'Unmapped source category') AS Category,
            n.category AS CategoryOriginal, n.name AS NoticeNameOriginal,
            n.reason AS ReasonOriginal, n.risk AS RiskOriginal, n.source_url AS SourceURL
        FROM notices n LEFT JOIN category_map m ON n.category=m.original
    """,
    "FactRecallLink": """
        SELECT r.notice_id::VARCHAR AS NoticeId, r.gtin AS ProductCode,
            r.name_conflict AS DescriptionReviewFlag, r.raw_blocks AS BatchTextOriginal
        FROM recall_product_review r
    """,
    "DimPriceDate": """
        SELECT value::DATE AS Date, year(value)::BIGINT AS Year,
               strftime(value,'%Y-%m') AS YearMonth, date_trunc('month',value)::DATE AS MonthStart
        FROM generate_series((SELECT min(observed_on) FROM prices)::TIMESTAMP,
                             (SELECT max(observed_on) FROM prices)::TIMESTAMP, INTERVAL 1 DAY) t(value)
    """,
    "DimRecallDate": """
        SELECT value::DATE AS Date, year(value)::BIGINT AS Year,
               strftime(value,'%Y-%m') AS YearMonth, date_trunc('month',value)::DATE AS MonthStart
        FROM generate_series((SELECT min(published_at)::DATE FROM notices)::TIMESTAMP,
                             (SELECT max(published_at)::DATE FROM notices)::TIMESTAMP, INTERVAL 1 DAY) t(value)
    """,
}

RELATIONSHIPS = [
    ("FactPrice", "ProductCode", "DimProduct", "ProductCode"),
    ("FactPrice", "LocationId", "DimLocation", "LocationId"),
    ("FactPrice", "ObservedDate", "DimPriceDate", "Date"),
    ("FactRecallLink", "ProductCode", "DimProduct", "ProductCode"),
    ("FactRecallLink", "NoticeId", "DimNotice", "NoticeId"),
    ("DimNotice", "PublishedDate", "DimRecallDate", "Date"),
]


def export_tables(database, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    with connect(database, read_only=True) as con:
        mapping = pa.table({"original": list(CATEGORY_EN), "english": list(CATEGORY_EN.values())})
        con.register("category_map", mapping)
        for name, query in QUERIES.items():
            path = destination / f"{name}.parquet"
            con.execute(
                f"COPY ({query}) TO $path (FORMAT PARQUET, COMPRESSION ZSTD)", {"path": str(path)}
            )
            sql_path = str(path).replace("'", "''")
            con.execute(f"CREATE TEMP VIEW \"{name}\" AS SELECT * FROM read_parquet('{sql_path}')")
            files.append(
                {
                    "table": name,
                    "rows": pq.ParquetFile(path).metadata.num_rows,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
        checks = {}
        for fact, foreign, dimension, key in RELATIONSHIPS:
            duplicates = con.execute(
                f'SELECT count(*)-count(DISTINCT "{key}") FROM "{dimension}"'
            ).fetchone()[0]
            orphans = con.execute(
                f'SELECT count(*) FROM "{fact}" f ANTI JOIN "{dimension}" d ON f."{foreign}"=d."{key}"'
            ).fetchone()[0]
            checks[f"{fact}.{foreign}"] = {
                "duplicate_dimension_keys": duplicates,
                "orphan_rows": orphans,
            }
            if duplicates or orphans:
                raise ValueError(
                    f"Invalid model relationship: {fact}.{foreign}: {checks[f'{fact}.{foreign}']}"
                )
        unmapped = con.execute(
            "SELECT count(*) FROM DimNotice WHERE Category='Unmapped source category'"
        ).fetchone()[0]
        source_report = json.loads(con.execute("SELECT report FROM build_report").fetchone()[0])
        report = {
            "source_scope": source_report["scope"],
            "source_built_at": source_report["built_at"],
            "files": files,
            "relationships": checks,
            "unmapped_categories": unmapped,
            "source_counts": source_report["counts"],
        }
    (destination / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
