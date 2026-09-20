import json

from .labels import category_english
from .pipeline import connect


def records(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def overview(database):
    with connect(database, read_only=True) as con:
        report = json.loads(con.execute("SELECT report FROM build_report").fetchone()[0])
        statuses = records(
            con.execute(
                "SELECT review_status AS label, count(*) AS value FROM catalogue GROUP BY 1 ORDER BY 2 DESC"
            )
        )
        months = records(
            con.execute("""SELECT strftime(published_at,'%Y-%m') AS label, count(*) AS value
            FROM notices WHERE published_at IS NOT NULL GROUP BY 1 ORDER BY 1""")
        )
        countries = records(
            con.execute("""SELECT upper(coalesce(nullif(country,''),'Unknown')) AS label, count(*) AS value
            FROM prices GROUP BY 1 ORDER BY 2 DESC LIMIT 8""")
        )
        coverage = records(
            con.execute("""SELECT
            CASE WHEN price_count>0 AND notice_count>0 THEN 'Products + prices + recalls'
                 WHEN price_count>0 THEN 'Products + prices'
                 WHEN notice_count>0 THEN 'Products + recalls'
                 ELSE 'Product record only' END AS label, count(*) AS value
            FROM catalogue GROUP BY 1 ORDER BY 2 DESC""")
        )
        categories = records(
            con.execute("""SELECT coalesce(nullif(category,''),'Unspecified') AS label, count(*) AS value
            FROM notices GROUP BY 1 ORDER BY 2 DESC LIMIT 8""")
        )
        for row in categories:
            row["source_label"] = row["label"]
            row["label"] = category_english(row["label"])
        return {
            "report": report,
            "statuses": statuses,
            "months": months,
            "countries": countries,
            "coverage": coverage,
            "categories": categories,
        }


def search(database, query="", status="all", page=1, page_size=20):
    filters, parameters = [], []
    if query:
        filters.append("(name ILIKE ? OR brand ILIKE ? OR raw_code = ? OR gtin = ?)")
        parameters.extend([f"%{query}%", f"%{query}%", query, query])
    statuses = {
        "recall_candidate",
        "description_conflict",
        "missing_name",
        "no_notice_found",
    }
    if status in statuses:
        filters.append("review_status = ?")
        parameters.append(status)
    if status == "priced":
        filters.append("price_count > 0")
    where = " WHERE " + " AND ".join(filters) if filters else ""
    with connect(database, read_only=True) as con:
        total = con.execute("SELECT count(*) FROM catalogue" + where, parameters).fetchone()[0]
        rows = records(
            con.execute(
                """SELECT gtin, raw_code, name, brand, quantity, price_count,
            notice_count, review_status, latest_price_date FROM catalogue"""
                + where
                + " ORDER BY notice_count DESC, price_count DESC, gtin LIMIT ? OFFSET ?",
                parameters + [page_size, (page - 1) * page_size],
            )
        )
    return {"rows": rows, "total": total, "page": page, "page_size": page_size}


def product(database, gtin):
    with connect(database, read_only=True) as con:
        found = records(con.execute("SELECT * FROM catalogue WHERE gtin = ?", [gtin]))
        if not found:
            return None
        notices = records(
            con.execute(
                """SELECT n.notice_id, n.name, n.published_at, n.reason, n.risk,
            n.source_url, r.raw_blocks, r.name_conflict
            FROM recall_product_review r JOIN notices n USING(notice_id) WHERE r.gtin=?
            ORDER BY n.published_at DESC""",
                [gtin],
            )
        )
        price_rows = records(
            con.execute(
                """SELECT price_id, price, currency, observed_on, price_per, discounted,
            country, city, store, location_id FROM prices WHERE gtin=? ORDER BY observed_on DESC, price_id DESC LIMIT 100""",
                [gtin],
            )
        )
        trend = records(
            con.execute(
                """SELECT strftime(observed_on, '%Y-%m') AS month, currency,
            coalesce(price_per, 'unit unspecified') AS unit, median(price) AS median_price, count(*) AS observations
            FROM prices WHERE gtin=? GROUP BY 1,2,3 ORDER BY 1,2,3""",
                [gtin],
            )
        )
        return {
            "product": found[0],
            "notices": notices,
            "prices": price_rows,
            "trend": trend,
        }
