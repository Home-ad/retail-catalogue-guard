import json
from datetime import UTC, datetime
from pathlib import Path

from .download import sha256
from .pipeline import connect

TABLES = [
    "products",
    "catalogue",
    "prices",
    "notices",
    "recall_links",
    "recall_product_review",
    "locations",
]


def export_demo(database, destination):
    destination = Path(destination)
    destination.mkdir(exist_ok=True, parents=True)
    with connect(database, read_only=True) as con:
        con.execute("""CREATE TEMP TABLE chosen AS
            SELECT gtin FROM catalogue
            QUALIFY row_number() OVER(PARTITION BY review_status ORDER BY price_count DESC, gtin)<=60""")
        predicates = {
            "products": "gtin IN (SELECT gtin FROM chosen)",
            "catalogue": "gtin IN (SELECT gtin FROM chosen)",
            "prices": "gtin IN (SELECT gtin FROM chosen)",
            "recall_links": "gtin IN (SELECT gtin FROM chosen)",
            "recall_product_review": "gtin IN (SELECT gtin FROM chosen)",
            "notices": "notice_id IN (SELECT notice_id FROM recall_links WHERE gtin IN (SELECT gtin FROM chosen))",
            "locations": "location_id IN (SELECT location_id FROM prices WHERE gtin IN (SELECT gtin FROM chosen))",
        }
        files = []
        for table in TABLES:
            path = destination / f"{table}.parquet"
            con.execute(
                f"COPY (SELECT * FROM {table} WHERE {predicates[table]}) TO $path (FORMAT PARQUET)",
                {"path": str(path)},
            )
            files.append(
                {
                    "table": table,
                    "file": path.name,
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                }
            )
        report = json.loads(con.execute("SELECT report FROM build_report").fetchone()[0])
        manifest = {
            "selection": "Up to 60 records per review status, prioritising observed prices. Purposive demo, not a representative sample.",
            "exported_at": datetime.now(UTC).isoformat(),
            "sources": report["sources"],
            "files": files,
        }
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_demo(source, data_directory):
    source, destination = Path(source), Path(data_directory)
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    destination.mkdir(exist_ok=True, parents=True)
    stage = destination / "demo.build.duckdb"
    if stage.exists():
        stage.unlink()
    con = connect(stage)
    for item in manifest["files"]:
        if item["table"] not in TABLES or Path(item["file"]).name != item["file"]:
            raise ValueError("Unexpected demo table or path")
        path = source / item["file"]
        if sha256(path) != item["sha256"]:
            raise ValueError(f"Demo checksum mismatch: {path.name}")
        con.execute(
            f"CREATE TABLE {item['table']} AS SELECT * FROM read_parquet(?)",
            [str(path)],
        )
    counts = {table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in TABLES}
    counts.update(
        {
            "product_source": counts["products"],
            "price_source": counts["prices"],
            "three_source_overlap": con.execute(
                "SELECT count(*) FROM catalogue WHERE price_count>0 AND notice_count>0"
            ).fetchone()[0],
        }
    )
    report = {
        "scope": "demo",
        "built_at": datetime.now(UTC).isoformat(),
        "counts": counts,
        "sources": manifest["sources"],
        "selection": manifest["selection"],
    }
    con.execute("CREATE TABLE build_report AS SELECT ?::JSON AS report", [json.dumps(report)])
    con.execute("CHECKPOINT")
    con.close()
    stage.replace(destination / "catalogue.duckdb")
    return report
