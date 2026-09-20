import json

import duckdb

from catalogue_guard.bi_export import export_tables
from catalogue_guard.bi_project import build_powerbi
from catalogue_guard.labels import category_english


def test_model_keeps_unmatched_evidence_and_safe_relationships(database, tmp_path):
    con = duckdb.connect(str(database))
    con.execute(
        "INSERT INTO recall_links VALUES ('1','04000915102574','4000915102574','Original batch')"
    )
    con.execute(
        "INSERT INTO recall_product_review VALUES ('1','04000915102574','4000915102574','Original batch',NULL,'Source name',false)"
    )
    con.close()
    report = export_tables(database, tmp_path / "bi")
    assert all(
        not item["orphan_rows"] and not item["duplicate_dimension_keys"]
        for item in report["relationships"].values()
    )
    con = duckdb.connect()
    extra = con.execute(
        "SELECT InProductCatalogue, HasRecallCandidate FROM read_parquet(?) WHERE ProductCode='04000915102574'",
        [str(tmp_path / "bi" / "DimProduct.parquet")],
    ).fetchone()
    assert extra == (False, True)


def test_native_project_uses_separate_facts_and_guarded_prices(database, tmp_path):
    root = tmp_path / "project"
    build_powerbi(database, root)
    model = json.loads((root / "Catalogue.SemanticModel" / "model.bim").read_text())
    assert len(model["model"]["relationships"]) == 6
    assert not any(r["toTable"].startswith("Fact") for r in model["model"]["relationships"])
    assert (root / "Retail Catalogue Guard.pbip").exists()
    measures = model["model"]["tables"][0]["measures"]
    median = next(m["expression"] for m in measures if m["name"] == "Median comparable price")
    assert median.count("HASONEVALUE") == 3
    build_powerbi(database, root)
    assert len(list((root / "Catalogue.Report" / "definition" / "pages").rglob("page.json"))) == 3


def test_english_category_preserves_unknown_as_explicit_gap():
    assert category_english("viandes") == "Meat"
    assert category_english("future category") == "Unmapped source category"
