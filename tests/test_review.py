import csv
import io

import pytest
from fastapi.testclient import TestClient

from catalogue_guard.review import export_csv, parse_catalogue, review_catalogue
from catalogue_guard.server import create_app


def test_catalogue_preserves_rows_and_uncertainty(database):
    result = review_catalogue(
        database,
        "sku,barcode,name,batch\nA,3017620422003,Poisson,LOT42\nA,3017620422004,Invalid,\nB,4000915102574,Absent,\n",
    )
    assert result["summary"]["rows"] == 3
    assert result["summary"]["matched_products"] == 1
    first = result["rows"][0]
    assert first["notice_count"] == 2
    assert first["price_count"] == 2
    assert first["batch_status"] == "manual_check_required"
    assert "catalogue_name_conflict" in first["issues"]
    assert "duplicate_sku" in first["issues"]
    assert "invalid_barcode" in result["rows"][1]["issues"]
    assert "product_not_in_snapshot" in result["rows"][2]["issues"]


def test_export_is_spreadsheet_safe(database):
    result = review_catalogue(database, 'sku,barcode,name\n=1+1,3017620422003,"@SUM(A1:A2)"\n')
    rows = list(csv.DictReader(io.StringIO(export_csv(result))))
    assert rows[0]["sku"] == "'=1+1"
    assert rows[0]["name"].startswith("'@")
    assert "https://example.com/recall/" in rows[0]["source_urls"]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "name,code\nx,1",
        "sku,barcode\n",
        "sku,barcode\na,b,c",
        "sku,barcode,barcode\na,b,c",
    ],
)
def test_invalid_csv_is_rejected(text):
    with pytest.raises(ValueError):
        parse_catalogue(text)


def test_api_workflow_and_errors(database):
    client = TestClient(create_app(database))
    assert client.get("/").status_code == 200
    assert client.get("/api/overview").json()["report"]["counts"]["three_source_overlap"] == 1
    assert client.get("/api/products", params={"q": "' OR 1=1 --"}).json()["total"] == 0
    detail = client.get("/api/products/3017620422003").json()
    assert len(detail["notices"]) == 2
    assert len(detail["prices"]) == 2
    assert client.get("/api/products/invalid").status_code == 404
    assert client.post("/api/review", content="wrong,csv").status_code == 400
    assert client.post("/api/review", content=b"\xff").status_code == 400
    assert client.post("/api/review", content="x" * 2_000_001).status_code == 413
    demo = client.get("/api/demo-catalogue").text
    assert client.post("/api/review", content=demo).json()["summary"]["rows"] == 1
    assert client.post("/api/review.csv", content=demo).status_code == 200
