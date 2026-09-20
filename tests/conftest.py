import json

import duckdb
import pytest

from catalogue_guard.pipeline import build


@pytest.fixture
def database(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    products = [
        {
            "code": "3017620422003",
            "product_name": [{"lang": "fr", "text": "Pâte noisettes"}],
            "brands": "Test brand",
            "quantity": "350 g",
            "product_quantity": "350",
            "product_quantity_unit": "g",
            "countries_tags": ["en:france"],
            "categories_tags": ["en:spreads"],
            "last_modified_t": 100,
        },
        {
            "code": "03017620422003",
            "product_name": [{"lang": "fr", "text": "Pâte noisettes"}],
            "brands": "Test brand",
            "quantity": "350 g",
            "product_quantity": "350",
            "product_quantity_unit": "g",
            "countries_tags": ["en:france"],
            "categories_tags": ["en:spreads"],
            "last_modified_t": 101,
        },
        {
            "code": "3017620422004",
            "product_name": [{"lang": "main", "text": "Invalid code"}],
            "brands": "Test",
            "quantity": "1 kg",
            "product_quantity": "1",
            "product_quantity_unit": "kg",
            "countries_tags": ["en:france"],
            "categories_tags": ["en:spreads"],
            "last_modified_t": 100,
        },
    ]
    prices = [
        {
            "id": index,
            "product_code": "3017620422003",
            "price": price,
            "currency": "EUR",
            "date": "2025-01-01",
            "price_per": "UNIT",
            "price_is_discounted": False,
            "price_without_discount": price,
            "location_id": 1,
            "proof_id": 2,
            "location_osm_address_country_code": "fr",
            "location_osm_address_city": "Paris",
            "location_osm_display_name": "Test store",
            "location_osm_lat": 48.8,
            "location_osm_lon": 2.3,
            "type": "PRODUCT",
        }
        for index, price in [(1, 3.5), (2, 4.0), (3, -1.0)]
    ]
    notices = [
        {
            "id": str(index),
            "categorie_produit": "alimentation",
            "numero_version": 1,
            "date_publication": "2025-01-01T00:00:00Z",
            "libelle": name,
            "marque_produit": "Test",
            "sous_categorie_produit": "Test food",
            "motif_rappel": "Test fixture only",
            "risques_encourus": "Test",
            "lien_vers_la_fiche_rappel": "https://example.com/recall/" + str(index),
            "date_debut_commercialisation": "2024-01-01",
            "date_date_fin_commercialisation": "2025-01-01",
            "identification_produits": [
                "3017620422003",
                "LOT42",
                "|garbled",
                "2025-01-01",
            ],
        }
        for index, name in [(1, "Pâte noisettes"), (2, "Poisson fumé")]
    ]
    (raw / "recalls.json").write_text(json.dumps(notices), encoding="utf-8")
    con = duckdb.connect()
    for name, data in [("products", products), ("prices", prices)]:
        source = raw / f"{name}.json"
        source.write_text(json.dumps(data), encoding="utf-8")
        con.execute(
            "COPY (SELECT * FROM read_json_auto($source)) TO $destination (FORMAT PARQUET)",
            {"source": str(source), "destination": str(raw / f"{name}.parquet")},
        )
    con.close()
    build(tmp_path)
    return tmp_path / "catalogue.duckdb"
