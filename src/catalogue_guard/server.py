import csv
import io
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import analytics
from .identifiers import canonical_gtin
from .review import export_csv, review_catalogue


def create_app(database):
    database = Path(database).resolve()
    if not database.exists():
        raise FileNotFoundError(f"Build or load a demo database first: {database}")
    app = FastAPI(title="Retail Catalogue Guard", version="1.0.0")
    static = Path(__file__).parent / "static"

    @app.get("/api/overview")
    @lru_cache(maxsize=1)
    def overview():
        return analytics.overview(database)

    @app.get("/api/products")
    def products(
        q: str = Query("", max_length=150),
        status: str = "all",
        page: int = Query(1, ge=1),
    ):
        return analytics.search(database, q, status, page)

    @app.get("/api/products/{code}")
    def product(code: str):
        gtin = canonical_gtin(code)
        result = analytics.product(database, gtin) if gtin else None
        if result is None:
            raise HTTPException(404, "Product not found in this snapshot")
        return result

    @app.get("/api/demo-catalogue")
    def demo_catalogue():
        with analytics.connect(database, read_only=True) as con:
            rows = con.execute("""SELECT raw_code, name FROM catalogue WHERE price_count>0
                ORDER BY notice_count DESC, price_count DESC, gtin LIMIT 25""").fetchall()
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["sku", "barcode", "name", "batch"])
        for index, (code, name) in enumerate(rows, 1):
            writer.writerow([f"DEMO-{index:03}", code, name, ""])
        return Response(
            stream.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="demo_catalogue.csv"'},
        )

    async def catalogue_body(request):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 2_000_000:
                raise HTTPException(413, "CSV must be smaller than 2 MB")
        try:
            return bytes(body).decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise HTTPException(400, "Save the CSV as UTF-8") from error

    @app.post("/api/review")
    async def review(request: Request):
        text = await catalogue_body(request)
        try:
            return review_catalogue(database, text)
        except (ValueError, csv.Error) as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/review.csv")
    async def review_csv(request: Request):
        text = await catalogue_body(request)
        try:
            result = review_catalogue(database, text)
        except (ValueError, csv.Error) as error:
            raise HTTPException(400, str(error)) from error
        return Response(
            export_csv(result),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="catalogue_review.csv"'},
        )

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    app.mount("/static", StaticFiles(directory=static), name="static")
    return app
