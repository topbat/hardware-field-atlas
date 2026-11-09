import json
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CATEGORIES = {
    "toy": "AI 玩具", "glasses": "AI 眼镜", "speaker": "AI 音箱",
    "mirror": "AI 镜子", "cabinet": "AI 柜子", "desk": "AI 电脑桌",
}
Category = Literal["toy", "glasses", "speaker", "mirror", "cabinet", "desk"]
Kind = Literal["commercial", "open", "reference", "module"]
Compute = Literal["device", "phone", "lan", "cloud", "mixed", "unknown"]
ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"


class StaleProduct(Exception):
    pass


def product_etag(product: dict) -> str:
    encoded = json.dumps(product, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return '"' + sha256(encoded).hexdigest() + '"'


def public_url(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme not in {"https", "http"} or not parsed.hostname
            or parsed.username or parsed.password or any(ch.isspace() for ch in value)):
        raise ValueError("使用有效的 HTTP 或 HTTPS 地址")
    return value


def asset_url(value: str) -> str:
    if value.startswith("/assets/") and re.fullmatch(r"/assets/[\w./-]+", value):
        if all(segment not in {"", ".", ".."} for segment in value[8:].split("/")):
            return value
    raise ValueError("使用 /assets/ 下的本地文件")


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Source(Record):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=180)
    url: str = Field(max_length=1800)
    type: Literal["official", "teardown", "open", "manual", "other"]
    locator: str | None = Field(default=None, max_length=600)
    note: str | None = Field(default=None, max_length=1000)

    _validate_url = field_validator("url")(public_url)


class EvidenceRecord(Record):
    sourceIds: list[str] = Field(max_length=25)


class Spec(EvidenceRecord):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=1500)


class Ability(EvidenceRecord):
    name: str = Field(min_length=1, max_length=120)
    input: str = Field(max_length=1200)
    compute: Compute
    output: str = Field(max_length=1200)
    offline: str = Field(max_length=1200)


class Part(EvidenceRecord):
    id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(max_length=1500)
    mpn: str | None = Field(max_length=180)
    manufacturer: str | None = Field(max_length=180)
    quantity: str = Field(max_length=100)
    status: Literal["confirmed", "observed", "inferred", "unknown"]
    sample: str | None = Field(max_length=180)


class ModelAsset(Record):
    url: str = Field(max_length=240)
    type: Literal["reconstruction", "concept", "official", "scan"]
    note: str = Field(min_length=1, max_length=1200)

    _validate_url = field_validator("url")(asset_url)


class ImageAsset(Record):
    url: str = Field(max_length=1800)
    alt: str = Field(min_length=1, max_length=240)
    type: Literal["concept", "official", "retail", "photo", "teardown"]
    sourceId: str | None = Field(default=None, max_length=64)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return asset_url(value) if value.startswith("/") else public_url(value)


class CutawayAsset(EvidenceRecord):
    url: str = Field(max_length=240)
    alt: str = Field(min_length=1, max_length=240)
    type: Literal["concept", "reconstruction"]
    note: str = Field(min_length=1, max_length=1200)

    _validate_url = field_validator("url")(asset_url)


class BuildGuide(Record):
    repo: str = Field(max_length=1800)
    steps: list[str] = Field(max_length=24)
    stepSourceIds: list[list[str]] | None = Field(default=None, max_length=24)
    note: str = Field(max_length=1800)

    _validate_url = field_validator("repo")(public_url)


class Product(Record):
    id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=1, max_length=160)
    brand: str = Field(min_length=1, max_length=160)
    category: Category
    kind: Kind
    origin: str = Field(min_length=1, max_length=120)
    tagline: str = Field(min_length=1, max_length=260)
    description: str = Field(min_length=1, max_length=3000)
    aliases: list[str] = Field(max_length=40)
    tags: list[str] = Field(max_length=40)
    revision: str = Field(min_length=1, max_length=240)
    checkedAt: date
    specs: list[Spec] = Field(max_length=100)
    abilities: list[Ability] = Field(max_length=50)
    parts: list[Part] = Field(max_length=200)
    sources: list[Source] = Field(min_length=1, max_length=60)
    model: ModelAsset | None
    image: ImageAsset | None = None
    photos: list[ImageAsset] = Field(default_factory=list, max_length=8)
    cutaway: CutawayAsset | None = None
    build: BuildGuide | None = None

    @model_validator(mode="after")
    def verify_evidence(self):
        sources = {source.id for source in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("来源编号必须唯一")
        if len({part.id for part in self.parts}) != len(self.parts):
            raise ValueError("部件编号必须唯一")
        if len({spec.key for spec in self.specs}) != len(self.specs):
            raise ValueError("规格编号必须唯一")
        for row in [*self.specs, *self.abilities, *self.parts]:
            if set(row.sourceIds) - sources:
                raise ValueError("存在未定义的来源编号")
        for photo in [*self.photos, *([self.image] if self.image else [])]:
            if photo.type != "concept" and not photo.sourceId:
                raise ValueError("实物图片须关联来源")
            if photo.sourceId is not None and photo.sourceId not in sources:
                raise ValueError("图片存在未定义的来源编号")
        if self.cutaway and (not self.cutaway.sourceIds or set(self.cutaway.sourceIds) - sources):
            raise ValueError("剖视图须关联有效来源")
        for part in self.parts:
            if part.status in {"confirmed", "observed"} and not part.sourceIds:
                raise ValueError(f"部件 {part.id} 缺少证据")
        if self.build and self.build.stepSourceIds is not None:
            if len(self.build.stepSourceIds) != len(self.build.steps):
                raise ValueError("复现步骤及来源列表长度必须一致")
            if any(set(ids) - sources for ids in self.build.stepSourceIds):
                raise ValueError("复现步骤存在未定义的来源编号")
        return self


class Correction(Record):
    productId: str = Field(pattern=ID_PATTERN)
    field: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=3, max_length=2000)
    url: str | None = Field(default=None, max_length=1800)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return public_url(value) if value is not None else None


class Moderation(Record):
    status: Literal["accepted", "dismissed"]


class CatalogStore:
    def __init__(self, seed_path: Path, data_dir: Path):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.database = data_dir / "catalog.sqlite3"
        raw = json.loads(seed_path.read_text(encoding="utf-8-sig"))
        products = [Product.model_validate(row).model_dump(mode="json") for row in raw["products"]]
        self.seed = {item["id"]: item for item in products}
        if not products or len(self.seed) != len(products):
            raise ValueError("目录须包含产品且产品编号必须唯一")
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id TEXT PRIMARY KEY, productId TEXT NOT NULL, field TEXT NOT NULL,
                    message TEXT NOT NULL, url TEXT, status TEXT NOT NULL DEFAULT 'pending',
                    createdAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS overrides (id TEXT PRIMARY KEY, content TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions (
                    id INTEGER PRIMARY KEY, productId TEXT NOT NULL, previous TEXT NOT NULL,
                    current TEXT NOT NULL, createdAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS revisions_product ON revisions(productId, id DESC);
            """)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.database, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def catalog(self) -> dict:
        with self.connect() as conn:
            overrides = {row["id"]: json.loads(row["content"])
                         for row in conn.execute("SELECT id, content FROM overrides")}
        return {"products": [overrides.get(key, product) for key, product in self.seed.items()]}

    def update(self, product_id: str, product: Product, expected: str | None = None) -> dict:
        updated = product.model_dump(mode="json")
        content = json.dumps(updated, ensure_ascii=False)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT content FROM overrides WHERE id = ?", (product_id,)).fetchone()
            previous = row["content"] if row else json.dumps(self.seed[product_id], ensure_ascii=False)
            previous_product = json.loads(previous)
            if expected is not None and expected != product_etag(previous_product):
                raise StaleProduct
            if previous_product != updated:
                conn.execute("INSERT INTO revisions (productId, previous, current) VALUES (?, ?, ?)",
                             (product_id, previous, content))
                conn.execute("INSERT INTO overrides VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET content=excluded.content",
                             (product_id, content))
        return updated


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def compact(value: str) -> str:
    return "".join(ch for ch in normalize(value) if ch.isalnum())


def matches(term: str, value: str) -> bool:
    value_normal = normalize(value)
    key = compact(term)
    return term in value_normal or bool(key and key in compact(value_normal))


def filter_catalog(products: list[dict], query: str, category: str | None, kind: str | None,
                   compute: str | None, model: bool | None, limit: int) -> dict:
    terms = normalize(query).split()
    found = []
    matched_parts = []
    counts = dict.fromkeys(CATEGORIES, 0)
    for product in products:
        if kind and product["kind"] != kind:
            continue
        if compute and not any(row["compute"] == compute for row in product["abilities"]):
            continue
        if model is not None and bool(product["model"]) != model:
            continue
        part_fields = [(part, [part["name"], part["mpn"] or "", part["manufacturer"] or ""])
                       for part in product["parts"]]
        descriptors = [product["id"], product["name"], product["brand"], product["tagline"],
                       CATEGORIES[product["category"]], product["revision"], *product["aliases"], *product["tags"]]
        fields = descriptors + [value for _, values in part_fields for value in values]
        fields += [row["name"] for row in product["abilities"]]
        if not all(any(matches(term, field) for field in fields) for term in terms):
            continue
        counts[product["category"]] += 1
        if category and product["category"] != category:
            continue
        found.append(product)
        for part, values in part_fields:
            if terms and all(any(matches(term, value) for value in values) for term in terms):
                matched_parts.append({"productId": product["id"], "productName": product["name"], "part": part})
    return {
        "products": found[:limit], "total": len(found), "parts": matched_parts[:150],
        "categories": [{"id": key, "label": label, "count": counts[key]} for key, label in CATEGORIES.items()],
    }
