from catalogue_guard.analytics import overview, product
from catalogue_guard.demo import export_demo, load_demo


def test_demo_roundtrip_keeps_scope_and_relationships(database, tmp_path):
    target = tmp_path / "demo"
    manifest = export_demo(database, target)
    assert len(manifest["files"]) == 7
    loaded = tmp_path / "loaded"
    report = load_demo(target, loaded)
    assert report["scope"] == "demo"
    assert report["counts"]["three_source_overlap"] == 1
    assert overview(loaded / "catalogue.duckdb")["report"]["scope"] == "demo"
    detail = product(loaded / "catalogue.duckdb", "03017620422003")
    assert len(detail["prices"]) == 2
    assert len(detail["notices"]) == 2
