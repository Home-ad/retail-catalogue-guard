import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

SOURCES = {
    "products": "https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet",
    "prices": "https://huggingface.co/datasets/openfoodfacts/open-prices/resolve/main/prices.parquet",
    "recalls": "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/rappelconso-v2-gtin-espaces/exports/json",
}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_source(name, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    suffix = ".json" if name == "recalls" else ".parquet"
    path = directory / (name + suffix)
    manifest_path = directory / (name + ".manifest.json")
    if path.exists() and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if path.stat().st_size == manifest["bytes"] and sha256(path) == manifest["sha256"]:
            print(f"Verified existing {name}: {manifest['bytes']:,} bytes", flush=True)
            return manifest
        raise ValueError(f"Snapshot checksum changed: {path}")
    partial = path.with_suffix(path.suffix + ".part")
    partial_metadata = path.with_suffix(path.suffix + ".part.json")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "RetailCatalogueGuard/1.0 public-data-download"}
    previous = None
    if offset:
        if not partial_metadata.exists():
            raise ValueError("Partial snapshot has no validator; use a new data directory")
        previous = json.loads(partial_metadata.read_text())
        if not previous.get("etag"):
            raise ValueError(
                "Source cannot safely resume without an ETag; use a new data directory"
            )
        headers["Range"] = f"bytes={offset}-"
        headers["If-Range"] = previous["etag"]
    url = SOURCES[name]
    with requests.get(url, headers=headers, stream=True, timeout=(30, 180)) as response:
        response.raise_for_status()
        etag = response.headers.get("ETag")
        if offset and response.status_code != 206:
            raise ValueError(
                "Server did not accept resume; keep the partial file and retry explicitly"
            )
        if previous and previous["etag"] != etag:
            raise ValueError("Source changed during download; use a new data directory")
        if response.status_code == 206:
            content_range = response.headers.get("Content-Range", "")
            if not content_range.startswith(f"bytes {offset}-"):
                raise ValueError(f"Unexpected response range: {content_range}")
            expected = int(content_range.rsplit("/", 1)[-1])
        else:
            size = response.headers.get("Content-Length")
            expected = int(size) if size else None
        partial_metadata.write_text(
            json.dumps({"url": url, "etag": etag, "expected_bytes": expected}),
            encoding="utf-8",
        )
        last_print = time.monotonic()
        with partial.open("ab" if offset else "wb") as stream:
            for chunk in response.iter_content(4 * 1024 * 1024):
                stream.write(chunk)
                offset += len(chunk)
                if time.monotonic() - last_print > 15:
                    print(
                        f"{name}: {offset / 1e9:.2f} GB / {(expected or 0) / 1e9:.2f} GB",
                        flush=True,
                    )
                    last_print = time.monotonic()
        if expected and offset != expected:
            raise ValueError(f"Incomplete download: {offset} of {expected}")
    if suffix == ".parquet":
        with partial.open("rb") as stream:
            start = stream.read(4)
            stream.seek(-4, 2)
            if start != b"PAR1" or stream.read(4) != b"PAR1":
                raise ValueError("Invalid Parquet file signature")
    else:
        json.loads(partial.read_text(encoding="utf-8"))
    partial.replace(path)
    manifest = {
        "source": name,
        "url": url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "etag": etag,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Complete {name}: {manifest['bytes']:,} bytes", flush=True)
    return manifest


if __name__ == "__main__":
    import sys

    download_source(sys.argv[1], sys.argv[2])
