import json
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .identifiers import canonical_gtin, name_conflict, recall_identifiers


def connect(path, read_only=False):
    connection = duckdb.connect(str(path), read_only=read_only)
    connection.execute("SET memory_limit='2GB'")
    connection.execute("SET threads=4")
    connection.execute("SET preserve_insertion_order=false")
    return connection


def write_json_lines(path, records):
    with path.open("w", encoding="utf-8") as stream:
        for row in records:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def prepare_recalls(raw, directory):
    records = json.loads(raw.read_text(encoding="utf-8"))
    notices, links, rejected = [], [], []
    for row in records:
        if row.get("categorie_produit") != "alimentation":
            continue
        notice_id = str(row["id"])
        notice = {
            "notice_id": notice_id,
            "version": row.get("numero_version") or 0,
            "published_at": row.get("date_publication"),
            "name": row.get("libelle") or row.get("modeles_ou_references"),
            "brand": row.get("marque_produit"),
            "category": row.get("sous_categorie_produit"),
            "reason": row.get("motif_rappel"),
            "risk": row.get("risques_encourus"),
            "source_url": row.get("lien_vers_la_fiche_rappel"),
            "sale_start": row.get("date_debut_commercialisation"),
            "sale_end": row.get("date_date_fin_commercialisation"),
            "raw_identification": json.dumps(
                row.get("identification_produits"), ensure_ascii=False
            ),
        }
        notices.append(notice)
        for code, gtin, block in recall_identifiers(row.get("identification_produits")):
            item = {
                "notice_id": notice_id,
                "version": notice["version"],
                "raw_code": code,
                "gtin": gtin,
                "raw_block": block,
            }
            (links if gtin else rejected).append(item)
    for name, rows in [
        ("notices", notices),
        ("recall_links", links),
        ("recall_rejected", rejected),
    ]:
        write_json_lines(directory / f"{name}.jsonl", rows)
    return len(records)


def project_source(source, destination, code_column, columns):
    source_file = pq.ParquetFile(source)
    writer = None
    count = 0
    try:
        for batch in source_file.iter_batches(batch_size=65536, columns=columns):
            table = pa.Table.from_batches([batch])
            identifiers = [canonical_gtin(code) for code in table[code_column].to_pylist()]
            table = table.append_column("gtin", pa.array(identifiers, type=pa.string()))
            if writer is None:
                writer = pq.ParquetWriter(destination, table.schema, compression="zstd")
            writer.write_table(table, row_group_size=65536)
            count += batch.num_rows
            if count % (65536 * 8) == 0:
                print(f"Projected {count:,} {code_column} records", flush=True)
    finally:
        if writer:
            writer.close()
        source_file.close()
    return count


def build(data_directory):
    started = time.monotonic()
    root = Path(data_directory).resolve()
    raw = root / "raw"
    prepared = root / "prepared"
    prepared.mkdir(exist_ok=True, parents=True)
    source_recall_rows = prepare_recalls(raw / "recalls.json", prepared)
    print(
        "Projecting relevant product columns into a compact Parquet snapshot",
        flush=True,
    )
    project_source(
        raw / "products.parquet",
        prepared / "products.parquet",
        "code",
        [
            "code",
            "product_name",
            "brands",
            "quantity",
            "product_quantity",
            "product_quantity_unit",
            "countries_tags",
            "categories_tags",
            "last_modified_t",
        ],
    )
    project_source(raw / "prices.parquet", prepared / "prices.parquet", "product_code", None)
    stage = root / "catalogue.build.duckdb"
    if stage.exists():
        stage.unlink()
    con = connect(stage)
    print("Reading complete product catalogue", flush=True)
    con.execute(
        """
        CREATE TABLE product_source AS
        SELECT code AS raw_code, gtin,
            coalesce(list_first(list_transform(list_filter(product_name, x -> x.lang = 'fr'), x -> x.text)),
                     list_first(list_transform(list_filter(product_name, x -> x.lang = 'main'), x -> x.text)),
                     list_first(list_transform(product_name, x -> x.text)), '') AS name,
            brands AS brand, quantity, product_quantity AS quantity_value,
            product_quantity_unit AS quantity_unit, countries_tags AS countries,
            categories_tags AS categories, last_modified_t AS modified_at
        FROM read_parquet(?)
    """,
        [str(prepared / "products.parquet")],
    )
    con.execute("""
        CREATE TABLE products AS
        SELECT *, count(*) OVER (PARTITION BY gtin) AS source_rows
        FROM product_source WHERE gtin IS NOT NULL
        QUALIFY row_number() OVER (PARTITION BY gtin ORDER BY modified_at DESC NULLS LAST, raw_code, name) = 1
    """)
    print("Normalising prices and source references", flush=True)
    con.execute(
        """
        CREATE TABLE price_source AS
        SELECT id AS price_id, product_code AS raw_code, gtin,
            price, currency, date AS observed_on, price_per, price_is_discounted AS discounted,
            price_without_discount, location_id, proof_id, location_osm_address_country_code AS country,
            location_osm_address_city AS city, location_osm_display_name AS store,
            location_osm_lat AS latitude, location_osm_lon AS longitude, type
        FROM read_parquet(?)
    """,
        [str(prepared / "prices.parquet")],
    )
    con.execute("""CREATE TABLE prices AS SELECT * FROM price_source
        WHERE gtin IS NOT NULL AND price > 0 AND currency IS NOT NULL AND observed_on IS NOT NULL
        QUALIFY row_number() OVER (PARTITION BY price_id ORDER BY observed_on DESC) = 1""")
    con.execute("""CREATE TABLE locations AS SELECT location_id, country, city, store, latitude, longitude
        FROM prices WHERE location_id IS NOT NULL
        QUALIFY row_number() OVER(PARTITION BY location_id ORDER BY observed_on DESC, price_id DESC) = 1""")
    for name in ["notices", "recall_links", "recall_rejected"]:
        con.execute(
            f"CREATE TABLE {name}_source AS SELECT * FROM read_json_auto(?, format='newline_delimited', sample_size=-1)",
            [str(prepared / f"{name}.jsonl")],
        )
    con.execute("""CREATE TABLE notices AS SELECT * EXCLUDE(published_at), try_cast(published_at AS TIMESTAMP) AS published_at
        FROM notices_source QUALIFY row_number() OVER(PARTITION BY notice_id ORDER BY version DESC) = 1""")
    con.execute("""CREATE TABLE recall_links AS
        SELECT l.notice_id, l.gtin, first(l.raw_code ORDER BY l.raw_code) AS raw_code,
               string_agg(DISTINCT l.raw_block, ' | ' ORDER BY l.raw_block) AS raw_blocks
        FROM recall_links_source l JOIN notices n ON l.notice_id = n.notice_id AND l.version = n.version
        GROUP BY l.notice_id, l.gtin""")
    con.execute("""CREATE TABLE recall_rejected AS SELECT r.* FROM recall_rejected_source r
        JOIN notices n ON r.notice_id=n.notice_id AND r.version=n.version""")
    review = con.execute("""SELECT l.*, p.name AS product_name, n.name AS recall_name
        FROM recall_links l JOIN notices n USING(notice_id) LEFT JOIN products p USING(gtin)""").to_arrow_table()
    conflicts = [
        name_conflict(left, right)
        for left, right in zip(
            review["product_name"].to_pylist(), review["recall_name"].to_pylist()
        )
    ]
    review = review.append_column("name_conflict", pa.array(conflicts, type=pa.bool_()))
    con.register("review_batch", review)
    con.execute("CREATE TABLE recall_product_review AS SELECT * FROM review_batch")
    con.unregister("review_batch")
    print("Building cardinality-safe catalogue views", flush=True)
    con.execute("""CREATE TABLE catalogue AS
        WITH price_counts AS (
            SELECT gtin, count(*) AS price_count, max(observed_on) AS latest_price_date,
                   count(DISTINCT location_id) AS store_count FROM prices GROUP BY gtin
        ), recall_counts AS (
            SELECT gtin, count(*) AS notice_count, bool_or(name_conflict) AS name_conflict
            FROM recall_product_review GROUP BY gtin
        )
        SELECT p.gtin, p.raw_code, p.name, p.brand, p.quantity, p.quantity_value, p.quantity_unit,
               p.countries, p.categories, p.source_rows,
               coalesce(v.price_count, 0) AS price_count, v.latest_price_date,
               coalesce(v.store_count, 0) AS store_count, coalesce(r.notice_count, 0) AS notice_count,
               coalesce(r.name_conflict, false) AS name_conflict,
               CASE WHEN coalesce(r.name_conflict,false) THEN 'description_conflict'
                    WHEN coalesce(r.notice_count,0)>0 THEN 'recall_candidate'
                    WHEN coalesce(p.name,'')='' THEN 'missing_name'
                    ELSE 'no_notice_found' END AS review_status
        FROM products p LEFT JOIN price_counts v USING(gtin) LEFT JOIN recall_counts r USING(gtin)
    """)
    con.execute("CREATE INDEX catalogue_gtin ON catalogue(gtin)")
    con.execute("CREATE INDEX prices_gtin ON prices(gtin)")
    con.execute("CREATE INDEX links_gtin ON recall_links(gtin)")
    counts = {
        table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in [
            "product_source",
            "products",
            "price_source",
            "prices",
            "notices",
            "recall_links",
            "recall_rejected",
            "catalogue",
            "locations",
        ]
    }
    assert counts["products"] == counts["catalogue"]
    assert (
        con.execute("SELECT sum(price_count) FROM catalogue").fetchone()[0]
        == con.execute(
            "SELECT count(*) FROM prices WHERE gtin IN (SELECT gtin FROM products)"
        ).fetchone()[0]
    )
    assert (
        con.execute("SELECT sum(notice_count) FROM catalogue").fetchone()[0]
        == con.execute(
            "SELECT count(*) FROM recall_links WHERE gtin IN (SELECT gtin FROM products)"
        ).fetchone()[0]
    )
    counts.update(
        {
            "recall_source_records": source_recall_rows,
            "recall_price_overlap": con.execute(
                "SELECT count(DISTINCT gtin) FROM recall_links WHERE gtin IN (SELECT gtin FROM prices)"
            ).fetchone()[0],
            "three_source_overlap": con.execute(
                "SELECT count(*) FROM catalogue WHERE price_count>0 AND notice_count>0"
            ).fetchone()[0],
            "description_conflicts": con.execute(
                "SELECT count(*) FROM catalogue WHERE name_conflict"
            ).fetchone()[0],
            "invalid_product_codes": con.execute(
                "SELECT count(*) FROM product_source WHERE gtin IS NULL"
            ).fetchone()[0],
            "duplicate_product_rows": counts["product_source"]
            - counts["products"]
            - con.execute("SELECT count(*) FROM product_source WHERE gtin IS NULL").fetchone()[0],
        }
    )
    manifests = [json.loads(path.read_text()) for path in sorted(raw.glob("*.manifest.json"))]
    report = {
        "built_at": datetime.now(UTC).isoformat(),
        "scope": "full",
        "counts": counts,
        "sources": manifests,
        "build_seconds": round(time.monotonic() - started, 2),
        "checks": {
            "product_grain_preserved": True,
            "price_totals_reconciled": True,
            "recall_totals_reconciled": True,
        },
    }
    con.execute("CREATE TABLE build_report AS SELECT ?::JSON AS report", [json.dumps(report)])
    con.execute("CHECKPOINT")
    con.close()
    stage.replace(root / "catalogue.duckdb")
    (root / "build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return report
