import pytest

from catalogue_guard.identifiers import (
    canonical_gtin,
    name_conflict,
    recall_identifiers,
)


@pytest.mark.parametrize("code", ["3017620422003", "03017620422003"])
def test_canonical_codes(code):
    assert canonical_gtin(code) == "03017620422003"


@pytest.mark.parametrize(
    "code",
    [
        None,
        "",
        "0000000000000",
        "3017620422004",
        "2025-01-01",
        "LOT123",
        "３０１７６２０４２２００３",
        "3.017620422003e12",
    ],
)
def test_rejects_invalid_identifiers(code):
    assert canonical_gtin(code) is None


def test_batches_are_not_parsed_as_extra_products():
    parsed = list(
        recall_identifiers(["3017620422003", "4000915102574", "|not-a-product", "3017620422003"])
    )
    assert [row[1] for row in parsed] == ["03017620422003", None]


def test_description_flag_is_conservative():
    assert name_conflict("Hareng fumé", "Bâtonnets de surimi")
    assert not name_conflict("Pâte aux noisettes", "pâte noisettes bio")
    assert not name_conflict("", "anything")
