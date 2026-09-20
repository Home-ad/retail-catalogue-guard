import csv
import io
from collections import Counter

from .analytics import records
from .identifiers import canonical_gtin, name_conflict
from .pipeline import connect


def parse_catalogue(text, limit=5000):
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
    if not reader.fieldnames or not {"sku", "barcode"}.issubset(reader.fieldnames):
        raise ValueError("CSV needs sku and barcode columns. Optional: name, batch.")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("CSV column names must be unique.")
    rows = []
    for index, row in enumerate(reader, 1):
        if index > limit:
            raise ValueError(f"Use at most {limit:,} catalogue rows per upload.")
        if None in row:
            raise ValueError(f"Row {index} has more values than the header.")
        if any(len(value or "") > 2000 for value in row.values()):
            raise ValueError(f"Row {index} has a field longer than 2,000 characters.")
        rows.append(
            {
                "row": index,
                **{
                    key: (row.get(key) or "").strip() for key in ["sku", "barcode", "name", "batch"]
                },
            }
        )
    if not rows:
        raise ValueError("The catalogue is empty.")
    return rows


def review_catalogue(database, text):
    inputs = parse_catalogue(text)
    sku_counts = Counter(row["sku"] for row in inputs if row["sku"])
    codes = sorted({code for row in inputs if (code := canonical_gtin(row["barcode"]))})
    products, notices = {}, {}
    if codes:
        with connect(database, read_only=True) as con:
            con.execute(
                "CREATE TEMP TABLE upload_codes AS SELECT unnest(?::VARCHAR[]) AS gtin",
                [codes],
            )
            products = {
                row["gtin"]: row
                for row in records(
                    con.execute("SELECT c.* FROM catalogue c JOIN upload_codes u USING(gtin)")
                )
            }
            for row in records(
                con.execute("""SELECT r.gtin, n.notice_id, n.source_url, n.name, n.published_at
                FROM recall_links r JOIN notices n USING(notice_id) JOIN upload_codes u USING(gtin)
                ORDER BY n.published_at DESC""")
            ):
                notices.setdefault(row["gtin"], []).append(row)
    output = []
    for row in inputs:
        gtin = canonical_gtin(row["barcode"])
        item = products.get(gtin)
        issues = []
        if not row["sku"]:
            issues.append("missing_sku")
        if sku_counts[row["sku"]] > 1:
            issues.append("duplicate_sku")
        if not gtin:
            issues.append("invalid_barcode")
        elif not item:
            issues.append("product_not_in_snapshot")
        if item:
            if not item["name"]:
                issues.append("missing_product_name")
            if item["source_rows"] > 1:
                issues.append("multiple_source_records")
            if name_conflict(row["name"], item["name"]):
                issues.append("catalogue_name_conflict")
            if item["name_conflict"]:
                issues.append("recall_description_conflict")
        candidates = notices.get(gtin, [])
        if candidates:
            issues.append("recall_candidate_check_batch")
        output.append(
            {
                **row,
                "gtin": gtin,
                "product_name": item["name"] if item else None,
                "brand": item["brand"] if item else None,
                "issues": issues,
                "status": "review_required" if issues else "no_issue_detected",
                "notice_count": len(candidates),
                "notices": candidates,
                "batch_status": "manual_check_required" if candidates else "not_assessed",
                "price_count": item["price_count"] if item else 0,
            }
        )
    counts = Counter(issue for row in output for issue in row["issues"])
    return {
        "rows": output,
        "summary": {
            "rows": len(output),
            "review_required": sum(bool(row["issues"]) for row in output),
            "matched_products": sum(row["gtin"] in products for row in output),
            "issues": dict(counts),
        },
        "notice": "Historical barcode candidates require product and batch verification. No issue detected does not establish product safety.",
    }


def export_csv(result):
    columns = [
        "row",
        "sku",
        "barcode",
        "gtin",
        "name",
        "product_name",
        "brand",
        "status",
        "issues",
        "notice_count",
        "batch",
        "batch_status",
        "price_count",
        "source_urls",
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for item in result["rows"]:
        row = {key: item.get(key, "") for key in columns}
        row["issues"] = " | ".join(item["issues"])
        row["source_urls"] = " | ".join(notice["source_url"] or "" for notice in item["notices"])
        for key, value in row.items():
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                row[key] = "'" + value
        writer.writerow(row)
    return stream.getvalue()
