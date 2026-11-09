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
    "phone": "AI 手机", "tablet": "AI 平板", "computer": "AI 电脑",
    "wearable": "智能穿戴", "earbuds": "AI 耳机", "recorder": "AI 录音",
    "education": "AI 学习设备", "vacuum": "扫地机器人", "security": "智能安防",
    "vehicle": "智能出行", "edge": "边缘计算", "imaging": "AI 影像",
    "outdoor": "庭院机器人", "pet": "智能养宠", "fabrication": "智能制造", "xr": "空间计算",
}
Category = Literal[
    "toy", "glasses", "speaker", "mirror", "cabinet", "desk", "phone", "tablet", "computer",
    "wearable", "earbuds", "recorder", "education", "vacuum", "security", "vehicle",
    "edge", "imaging", "outdoor", "pet", "fabrication", "xr",
]
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


class IllustrationPanels(Record):
    overview: str = Field(max_length=240)
    detail: str = Field(max_length=240)
    specs: str = Field(max_length=240)
    angles: str = Field(max_length=240)

    _validate_urls = field_validator("overview", "detail", "specs", "angles")(asset_url)


class VisualCard(EvidenceRecord):
    url: str = Field(max_length=240)
    title: str = Field(min_length=1, max_length=120)
    caption: str = Field(min_length=1, max_length=400)
    partId: str | None = Field(default=None, pattern=ID_PATTERN)

    _validate_url = field_validator("url")(asset_url)


class VisualBreakdown(Record):
    details: list[VisualCard] = Field(min_length=1, max_length=30)
    angles: list[VisualCard] = Field(min_length=2, max_length=12)


class IllustrationPlate(EvidenceRecord):
    url: str = Field(max_length=240)
    technical: Literal["teardown", "functional"]
    exterior: Literal["reference", "concept"]
    panels: IllustrationPanels | None = None
    breakdown: VisualBreakdown | None = None

    _validate_url = field_validator("url")(asset_url)



class BuildGuide(Record):
    repo: str = Field(max_length=1800)
    steps: list[str] = Field(max_length=24)
    stepSourceIds: list[list[str]] | None = Field(default=None, max_length=24)
    note: str = Field(max_length=1800)

    _validate_url = field_validator("repo")(public_url)


class EngineeringEvidence(EvidenceRecord):
    sourceIds: list[str] = Field(min_length=1, max_length=25)


class EngineeringSku(EngineeringEvidence):
    id: str = Field(pattern=ID_PATTERN)
    code: str = Field(min_length=1, max_length=120)
    module: str = Field(min_length=1, max_length=120)
    flash: str = Field(min_length=1, max_length=100)
    psram: str = Field(min_length=1, max_length=100)
    spiVoltage: str | None = Field(default=None, max_length=80)


class EngineeringFile(EngineeringEvidence):
    id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["schematic", "pcb", "gerber", "bom", "placement", "archive", "mechanical", "firmware", "datasheet"]
    url: str = Field(max_length=1800)
    note: str = Field(max_length=600)
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    _validate_url = field_validator("url")(public_url)


class EngineeringFirmware(EngineeringEvidence):
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    fileId: str = Field(pattern=ID_PATTERN)
    pinIds: list[str] = Field(min_length=1, max_length=64)
    note: str = Field(max_length=700)


class EngineeringRail(EngineeringEvidence):
    id: str = Field(pattern=ID_PATTERN)
    label: str = Field(min_length=1, max_length=120)
    volts: float = Field(ge=-1000, le=1000)
    note: str = Field(max_length=600)


REFERENCE_PATTERN = r"^[A-Za-z][A-Za-z0-9_-]{0,23}$"


class EngineeringPin(EngineeringEvidence):
    id: str = Field(pattern=ID_PATTERN)
    label: str = Field(min_length=1, max_length=120)
    signal: str = Field(min_length=1, max_length=240)
    railId: str | None = Field(default=None, pattern=ID_PATTERN)
    ref: str | None = Field(default=None, pattern=REFERENCE_PATTERN)
    note: str = Field(max_length=600)


class EngineeringBomItem(EngineeringEvidence):
    ref: str = Field(pattern=REFERENCE_PATTERN)
    name: str = Field(min_length=1, max_length=160)
    value: str = Field(max_length=220)
    package: str = Field(max_length=140)
    mpn: str | None = Field(default=None, max_length=180)
    fit: Literal["fitted", "dnp", "unknown"]


class EngineeringPlacement(Record):
    ref: str = Field(pattern=REFERENCE_PATTERN)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    side: Literal["top", "bottom"]
    rotation: float | None = Field(default=None, ge=-360, le=360)


class EngineeringBoard(EngineeringEvidence):
    coordinateSource: Literal["placement", "projection"] = "projection"
    width: float = Field(gt=0, le=3000)
    height: float = Field(gt=0, le=3000)
    placements: list[EngineeringPlacement] = Field(min_length=1, max_length=500)


class EngineeringRevision(EngineeringEvidence):
    id: str = Field(pattern=ID_PATTERN)
    label: str = Field(min_length=1, max_length=100)
    note: str = Field(min_length=1, max_length=1000)
    skuIds: list[str] = Field(min_length=1, max_length=40)
    firmware: list[EngineeringFirmware] = Field(max_length=20)
    rails: list[EngineeringRail] = Field(max_length=64)
    pins: list[EngineeringPin] = Field(max_length=200)
    files: list[EngineeringFile] = Field(min_length=1, max_length=60)
    bom: list[EngineeringBomItem] = Field(max_length=500)
    board: EngineeringBoard | None = None

    @model_validator(mode="after")
    def verify_links(self):
        files = {row.id: row for row in self.files}
        pins = {row.id for row in self.pins}
        rails = {row.id for row in self.rails}
        refs = {row.ref for row in self.bom}
        if (len(files) != len(self.files) or len(pins) != len(self.pins)
                or len(rails) != len(self.rails) or len(refs) != len(self.bom)):
            raise ValueError("版本内的文件、引脚、电源和 BOM 位号须唯一")
        for firmware in self.firmware:
            file = files.get(firmware.fileId)
            if not file or file.kind != "firmware" or set(firmware.pinIds) - pins:
                raise ValueError("固件须关联同一板版的固件源文件和引脚")
        for pin in self.pins:
            if (pin.railId and pin.railId not in rails) or (pin.ref and pin.ref not in refs):
                raise ValueError("引脚须关联同一板版的电源域和 BOM 位号")
        if self.board:
            placements = self.board.placements
            if len({point.ref for point in placements}) != len(placements):
                raise ValueError("PCB 位号坐标须唯一")
            for point in placements:
                if point.ref not in refs or point.x > self.board.width or point.y > self.board.height:
                    raise ValueError("PCB 位号须关联 BOM，坐标须落在板框内")
        return self

    def evidence(self):
        yield self
        yield from self.firmware
        yield from self.rails
        yield from self.pins
        yield from self.files
        yield from self.bom
        if self.board:
            yield self.board


class EngineeringArchive(Record):
    skus: list[EngineeringSku] = Field(min_length=1, max_length=40)
    revisions: list[EngineeringRevision] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def verify_skus(self):
        sku_ids = {sku.id for sku in self.skus}
        if (len(sku_ids) != len(self.skus)
                or len({revision.id for revision in self.revisions}) != len(self.revisions)):
            raise ValueError("SKU 与板版编号须各自唯一")
        for revision in self.revisions:
            if len(set(revision.skuIds)) != len(revision.skuIds) or set(revision.skuIds) - sku_ids:
                raise ValueError("板版须关联有效且唯一的 SKU")
        return self

    def evidence(self):
        yield from self.skus
        for revision in self.revisions:
            yield from revision.evidence()


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
    illustration: IllustrationPlate | None = None
    build: BuildGuide | None = None
    engineering: EngineeringArchive | None = None

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
        if self.illustration and (not self.illustration.sourceIds or set(self.illustration.sourceIds) - sources):
            raise ValueError("AI 图解须关联有效参考资料")
        if self.illustration and self.illustration.breakdown:
            breakdown = self.illustration.breakdown
            cards = [*breakdown.details, *breakdown.angles]
            part_ids = {part.id for part in self.parts}
            if len({card.url for card in cards}) != len(cards):
                raise ValueError("图卡须使用独立图片")
            for card in cards:
                if not card.sourceIds or set(card.sourceIds) - sources:
                    raise ValueError("图卡须关联有效参考资料")
                if card.partId and card.partId not in part_ids:
                    raise ValueError("图卡须关联有效部件")
        for part in self.parts:
            if part.status in {"confirmed", "observed"} and not part.sourceIds:
                raise ValueError(f"部件 {part.id} 缺少证据")
        if self.engineering and any(set(row.sourceIds) - sources for row in self.engineering.evidence()):
            raise ValueError("engineering 档案存在未定义的来源编号")
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
                   compute: str | None, model: bool | None, limit: int, offset: int = 0) -> dict:
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
        if product.get("engineering"):
            fields += [value for sku in product["engineering"]["skus"] for value in (sku["code"], sku["module"])]
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
        "products": found[offset:offset + limit], "total": len(found), "parts": matched_parts[:150],
        "categories": [{"id": key, "label": label, "count": counts[key]} for key, label in CATEGORIES.items()],
    }
