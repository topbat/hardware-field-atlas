import csv
import io
import json
import os
import secrets
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .catalog import (
    CatalogStore, Category, Compute, Correction, Kind, Moderation, Product, StaleProduct, filter_catalog, product_etag,
)

ROOT = Path(__file__).resolve().parents[2]
BODY_LIMIT = 3 * 1024 * 1024


class BodyLimit:
    """Limit JSON mutations before parsing, including chunked requests."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            chunk = event.get("body", b"")
            if len(body) + len(chunk) > BODY_LIMIT:
                await JSONResponse({"detail": "请求体不能超过 3 MiB"}, 413)(scope, receive, send)
                return
            body.extend(chunk)
            if not event.get("more_body"):
                break
        consumed = False

        async def replay():
            nonlocal consumed
            if consumed:
                return await receive()
            consumed = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)


def csv_cell(value: str | None) -> str:
    value = value or ""
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def create_app(seed_path: Path | None = None, data_dir: Path | None = None,
               web_dist: Path | None = None, research: bool = True) -> FastAPI:
    seed_path = seed_path or Path(os.environ.get("ATLAS_CATALOG", ROOT / "data/catalog.json"))
    data_dir = data_dir or Path(os.environ.get("ATLAS_DATA_DIR", ROOT / "runtime"))
    web_dist = web_dist or ROOT / "web/dist"
    store = CatalogStore(seed_path, data_dir)
    with store.connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS correction_limits (
                client TEXT PRIMARY KEY, window INTEGER NOT NULL, count INTEGER NOT NULL
            )
        """)
    app = FastAPI(title="硬件志 API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json",
                  redoc_url=None, swagger_ui_oauth2_redirect_url=None)
    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path.startswith(("/api/research", "/api/admin")):
            response.headers["Cache-Control"] = "no-store"
        return response

    def product_by_id(product_id: str) -> dict:
        for product in store.catalog()["products"]:
            if product["id"] == product_id:
                return product
        raise HTTPException(404, "未找到设备")

    def require_admin(authorization: Annotated[str | None, Header()] = None):
        token = os.environ.get("ATLAS_ADMIN_TOKEN")
        if not token:
            raise HTTPException(503, "审核入口未启用")
        prefix, _, provided = (authorization or "").partition(" ")
        if prefix.casefold() != "bearer" or not secrets.compare_digest(provided.encode(), token.encode()):
            raise HTTPException(401, "需要审核凭据", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/api/health")
    def health():
        with store.connect() as conn:
            conn.execute("SELECT 1 FROM overrides LIMIT 1")
        return {"status": "ok"}

    @app.get("/api/catalog")
    def catalog(q: Annotated[str, Query(max_length=160)] = "", category: Category | None = None,
                kind: Kind | None = None, compute: Compute | None = None, model: bool | None = None,
                limit: Annotated[int, Query(ge=1, le=200)] = 100):
        return filter_catalog(store.catalog()["products"], q, category, kind, compute, model, limit)

    @app.get("/api/products/{product_id}")
    def detail(product_id: str, response: Response):
        product = product_by_id(product_id)
        response.headers["ETag"] = product_etag(product)
        response.headers["Cache-Control"] = "no-cache"
        return product

    @app.get("/api/compare")
    def compare(ids: Annotated[str, Query(max_length=260)]):
        keys = [key.strip() for key in ids.split(",")]
        if not 2 <= len(keys) <= 4 or not all(keys) or len(set(keys)) != len(keys):
            raise HTTPException(422, "请选择 2–4 款不同设备")
        products = {product["id"]: product for product in store.catalog()["products"]}
        if any(key not in products for key in keys):
            raise HTTPException(404, "未找到对比设备")
        return {"products": [products[key] for key in keys]}

    @app.get("/api/products/{product_id}/bom.csv")
    def bom_csv(product_id: str):
        product = product_by_id(product_id)
        sources = {source["id"]: source["url"] for source in product["sources"]}
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["部件编号", "名称", "作用", "厂商料号", "厂商", "数量", "状态", "样机", "证据"])
        for part in product["parts"]:
            values = [part[key] for key in ("id", "name", "role", "mpn", "manufacturer", "quantity", "status", "sample")]
            values.append(" | ".join(sources[key] for key in part["sourceIds"]))
            writer.writerow([csv_cell(value) for value in values])
        return Response(buffer.getvalue().encode("utf-8-sig"), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{product_id}-bom.csv"'})

    @app.post("/api/corrections", status_code=201)
    def submit_correction(body: Correction, request: Request):
        import time
        from hashlib import sha256

        product_by_id(body.productId)
        identifier = uuid4().hex
        window = int(time.time()) // 3600
        client = sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
        with store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM correction_limits WHERE window < ?", (window,))
            count = conn.execute("SELECT count FROM correction_limits WHERE client = ?", (client,)).fetchone()
            total = conn.execute("SELECT COALESCE(SUM(count), 0) FROM correction_limits").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM corrections WHERE status='pending'").fetchone()[0]
            if (count and count[0] >= 12) or total >= 120 or pending >= 2000:
                raise HTTPException(429, "提交次数达到上限，请稍后再试", headers={"Retry-After": "3600"})
            conn.execute("INSERT INTO correction_limits VALUES (?, ?, 1) "
                         "ON CONFLICT(client) DO UPDATE SET count=count+1", (client, window))
            conn.execute("INSERT INTO corrections (id, productId, field, message, url) VALUES (?, ?, ?, ?, ?)",
                         (identifier, body.productId, body.field, body.message, body.url))
        return {"id": identifier, "status": "pending"}

    @app.get("/api/admin/corrections", dependencies=[Depends(require_admin)])
    def corrections(limit: Annotated[int, Query(ge=1, le=200)] = 100,
                    offset: Annotated[int, Query(ge=0)] = 0):
        with store.connect() as conn:
            rows = conn.execute("SELECT * FROM corrections ORDER BY createdAt DESC, id DESC LIMIT ? OFFSET ?",
                                (limit, offset)).fetchall()
        return {"corrections": [dict(row) for row in rows]}

    @app.patch("/api/admin/corrections/{identifier}", dependencies=[Depends(require_admin)])
    def moderate(identifier: str, body: Moderation):
        with store.connect() as conn:
            result = conn.execute("UPDATE corrections SET status = ? WHERE id = ?", (body.status, identifier))
            if not result.rowcount:
                raise HTTPException(404, "未找到纠错记录")
        return {"id": identifier, "status": body.status}

    @app.put("/api/admin/products/{product_id}", dependencies=[Depends(require_admin)])
    def update_product(product_id: str, product: Product, response: Response,
                       if_match: Annotated[str | None, Header()] = None):
        if product_id != product.id:
            raise HTTPException(422, "产品编号必须匹配")
        product_by_id(product_id)
        try:
            updated = store.update(product_id, product, expected=if_match)
        except StaleProduct:
            raise HTTPException(412, "当前档案已更新。请保留草稿，重新载入后合并。") from None
        response.headers["ETag"] = product_etag(updated)
        return updated

    @app.get("/api/admin/products/{product_id}/revisions", dependencies=[Depends(require_admin)])
    def revisions(product_id: str, limit: Annotated[int, Query(ge=1, le=100)] = 30,
                  offset: Annotated[int, Query(ge=0)] = 0):
        product_by_id(product_id)
        with store.connect() as conn:
            rows = conn.execute("SELECT * FROM revisions WHERE productId = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                                (product_id, limit, offset)).fetchall()
        return {"revisions": [{**dict(row), "previous": json.loads(row["previous"]),
                               "current": json.loads(row["current"])} for row in rows]}

    if research:
        from .research import create_research_router
        app.include_router(create_research_router(data_dir, store.catalog), prefix="/api")

    if (web_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")
    if (web_dist / "index.html").is_file():
        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str):
            if path == "api" or path.startswith("api/") or "." in path:
                raise HTTPException(404, "页面不存在")
            return FileResponse(web_dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app
