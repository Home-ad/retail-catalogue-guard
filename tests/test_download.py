import json

import pytest

from catalogue_guard.download import download_source


def test_resume_requires_original_validator(tmp_path):
    (tmp_path / "products.parquet.part").write_bytes(b"PAR1partial")
    with pytest.raises(ValueError, match="no validator"):
        download_source("products", tmp_path)


def test_changed_snapshot_cannot_be_appended(tmp_path, monkeypatch):
    (tmp_path / "products.parquet.part").write_bytes(b"PAR1partial")
    (tmp_path / "products.parquet.part.json").write_text(json.dumps({"etag": "old"}))

    class Response:
        status_code = 206
        headers = {"ETag": "new", "Content-Range": "bytes 11-20/21"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raise_for_status(self):
            return None

    monkeypatch.setattr("catalogue_guard.download.requests.get", lambda *args, **kwargs: Response())
    with pytest.raises(ValueError, match="Source changed"):
        download_source("products", tmp_path)
    assert (tmp_path / "products.parquet.part").read_bytes() == b"PAR1partial"
