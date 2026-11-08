import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

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
        update = client.get("/api/products/one").json()
        update["parts"][0]["sourceIds"] = ["missing"]
        assert client.put("/api/admin/products/one", headers=headers, json=update).status_code == 422
        update["parts"][0]["sourceIds"] = ["s1"]
        update["name"] = "已修订眼镜"
        assert client.put("/api/admin/products/one", headers=headers, json=update).status_code == 200
    with TestClient(create_app(seed, state, research=False)) as client:
        assert client.get("/api/products/one").json()["name"] == "已修订眼镜"
        assert client.get("/api/admin/corrections", headers=headers).json()["corrections"][0]["status"] == "accepted"
        snapshots = client.get("/api/admin/products/one/revisions", headers=headers).json()["revisions"]
        assert snapshots[0]["previous"]["name"] == "实验眼镜"

