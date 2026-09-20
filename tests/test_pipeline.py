import json

from catalogue_guard.pipeline import build, connect


def test_join_grains_do_not_multiply_prices(database):
    with connect(database, read_only=True) as con:
        row = con.execute(
            "SELECT price_count, notice_count, source_rows, name_conflict FROM catalogue"
        ).fetchone()
        assert row == (2, 2, 2, True)
        report = json.loads(con.execute("SELECT report FROM build_report").fetchone()[0])
        assert report["counts"]["invalid_product_codes"] == 1
        assert report["counts"]["recall_rejected"] == 2


def test_rebuild_is_idempotent(database):
    with connect(database, read_only=True) as con:
        original = json.loads(con.execute("SELECT report FROM build_report").fetchone()[0])[
            "counts"
        ]
    repeated = build(database.parent)
    assert repeated["counts"] == original
