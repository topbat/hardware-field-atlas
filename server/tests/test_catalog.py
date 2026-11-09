import csv
import io
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from atlas.catalog import Product
from atlas.main import create_app


@pytest.fixture
def seed(tmp_path):
    source = {"id": "s1", "title": "样机拆解", "url": "https://example.com/tear", "type": "teardown"}
    common = {
        "name": "实验眼镜", "brand": "实验品牌", "category": "glasses", "kind": "commercial",
        "origin": "中国", "tagline": "相机眼镜", "description": "工程样机",
        "aliases": ["Glass One"], "tags": [], "revision": "V1", "checkedAt": "2026-11-08",
        "specs": [], "abilities": [], "sources": [source], "model": None,
        "parts": [{
            "id": "soc", "name": "主控", "role": "处理", "mpn": "ABC-123",
            "manufacturer": "厂商", "quantity": "1", "status": "observed", "sample": "样机1",
            "sourceIds": ["s1"],
        }],
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"products": [
        {"id": "one", **common}, {"id": "two", **common, "name": "语音样机", "category": "speaker",
                                   "parts": [], "aliases": []},
    ]}), encoding="utf-8")
    return path


def test_part_reverse_lookup_and_csv(seed, tmp_path):
    with TestClient(create_app(seed, tmp_path / "state", research=False)) as client:
        result = client.get("/api/catalog", params={"q": "abc123"}).json()
        assert [row["id"] for row in result["products"]] == ["one"]
        assert result["parts"][0]["part"]["sourceIds"] == ["s1"]
        assert client.get("/api/catalog", params={"q": "Glass One", "category": "speaker"}).json()["total"] == 0
        assert client.get("/api/compare", params={"ids": "two,one"}).json()["products"][0]["id"] == "two"
        assert client.get("/api/compare", params={"ids": "one,one"}).status_code == 422
        response = client.get("/api/products/one/bom.csv")
        assert "attachment" in response.headers["content-disposition"]
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        assert "ABC-123" in rows[1]
        assert "https://example.com/tear" in rows[1]


def test_catalog_pages_keep_filter_counts(seed, tmp_path):
    with TestClient(create_app(seed, tmp_path / "state", research=False)) as client:
        first = client.get("/api/catalog", params={"limit": 1}).json()
        second = client.get("/api/catalog", params={"limit": 1, "offset": 1}).json()
        assert [row["id"] for row in first["products"]] == ["one"]
        assert [row["id"] for row in second["products"]] == ["two"]
        assert first["total"] == second["total"] == 2
        assert first["categories"] == second["categories"]
        assert client.get("/api/catalog", params={"offset": -1}).status_code == 422


def test_moderation_and_revisions_persist(seed, tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_ADMIN_TOKEN", "example-test-token")
    state = tmp_path / "state"
    headers = {"Authorization": "Bearer example-test-token"}
    with TestClient(create_app(seed, state, research=False)) as client:
        report = client.post("/api/corrections", json={
            "productId": "one", "field": "soc", "message": "请核对料号后缀",
        }).json()
        assert client.get("/api/admin/corrections").status_code == 401
        assert client.patch(f"/api/admin/corrections/{report['id']}", headers=headers,
                            json={"status": "accepted"}).status_code == 200
        original = client.get("/api/products/one")
        update = original.json()
        conditional = {**headers, "If-Match": original.headers["etag"]}
        update["parts"][0]["sourceIds"] = ["missing"]
        assert client.put("/api/admin/products/one", headers=headers, json=update).status_code == 422
        update["parts"][0]["sourceIds"] = ["s1"]
        update["name"] = "已修订眼镜"
        saved = client.put("/api/admin/products/one", headers=conditional, json=update)
        assert saved.status_code == 200
        assert saved.headers["etag"] != original.headers["etag"]
        update["name"] = "过期草稿"
        assert client.put("/api/admin/products/one", headers=conditional, json=update).status_code == 412
    with TestClient(create_app(seed, state, research=False)) as client:
        assert client.get("/api/products/one").json()["name"] == "已修订眼镜"
        assert client.get("/api/admin/corrections", headers=headers).json()["corrections"][0]["status"] == "accepted"
        snapshots = client.get("/api/admin/products/one/revisions", headers=headers).json()["revisions"]
        assert snapshots[0]["previous"]["name"] == "实验眼镜"


def test_photos_and_cutaways_keep_provenance_separate(seed):
    product = json.loads(seed.read_text(encoding="utf-8"))["products"][0]
    product["image"] = {"url": "https://example.com/product.png", "alt": "样机外观", "type": "retail"}
    with pytest.raises(ValidationError, match="实物图片须关联来源"):
        Product.model_validate(product)

    product["image"]["sourceId"] = "s1"
    product["cutaway"] = {
        "url": "/assets/cutaways/one.webp", "alt": "结构重绘",
        "type": "reconstruction", "note": "结构位置近似", "sourceIds": ["wrong"],
    }
    with pytest.raises(ValidationError, match="剖视图须关联有效来源"):
        Product.model_validate(product)

    product["cutaway"]["sourceIds"] = ["s1"]
    verified = Product.model_validate(product)
    assert verified.image.type == "retail"
    assert verified.cutaway.type == "reconstruction"



@pytest.fixture
def engineering_seed(seed):
    product = json.loads(seed.read_text(encoding="utf-8"))["products"][0]
    evidence = {"sourceIds": ["s1"]}
    product["engineering"] = {
        "skus": [{"id": "n8", "code": "BOARD-N8", "module": "MODULE-N8",
                  "flash": "8 MB", "psram": "无", **evidence}],
        "revisions": [{
            "id": "v11", "label": "v1.1", "note": "参考板", "skuIds": ["n8"], **evidence,
            "files": [{"id": "blink", "name": "Blink", "kind": "firmware", "note": "",
                       "url": "https://example.com/blink", **evidence}],
            "firmware": [{"name": "Blink", "version": "1", "fileId": "blink",
                          "pinIds": ["led"], "note": "参考示例", **evidence}],
            "rails": [{"id": "3v3", "label": "3V3", "volts": 3.3, "note": "", **evidence}],
            "pins": [{"id": "led", "label": "LED", "signal": "GPIO38", "railId": "3v3",
                      "ref": "D1", "note": "", **evidence}],
            "bom": [{"ref": "D1", "name": "LED", "value": "RGB", "package": "5050",
                     "fit": "fitted", **evidence}],
            "board": {"width": 20, "height": 40, **evidence,
                      "placements": [{"ref": "D1", "x": 4, "y": 8, "side": "top", "rotation": 90}]},
        }],
    }
    return product


def test_engineering_bundle_preserves_versioned_references(engineering_seed):
    board = Product.model_validate(engineering_seed).engineering.revisions[0]
    assert board.board.placements[0].ref == board.bom[0].ref == board.pins[0].ref
    assert board.firmware[0].pinIds == [board.pins[0].id]


@pytest.mark.parametrize("invalid", ["ref", "position", "pin", "source", "sku"])
def test_engineering_rejects_inconsistent_revision(engineering_seed, invalid):
    revision = engineering_seed["engineering"]["revisions"][0]
    if invalid == "ref":
        revision["board"]["placements"][0]["ref"] = "D2"
    elif invalid == "position":
        revision["board"]["placements"][0]["x"] = 21
    elif invalid == "pin":
        revision["firmware"][0]["pinIds"] = ["missing"]
    elif invalid == "source":
        revision["bom"][0]["sourceIds"] = ["unregistered"]
    else:
        revision["skuIds"] = ["unregistered"]
    with pytest.raises(ValidationError, match="engineering"):
        Product.model_validate(engineering_seed)
