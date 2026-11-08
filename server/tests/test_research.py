import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from atlas.research import ModelProvider, create_research_router


PRODUCT = {
    "id": "example-toy",
    "name": "小智样机",
    "brand": "样本",
    "category": "toy",
    "kind": "open",
    "aliases": ["语音机器人"],
    "tags": [],
    "sources": [
        {"id": "source", "title": "固件", "url": "https://example.com/source"},
        {"id": "board", "title": "硬件规格", "url": "https://example.com/board"},
        {"id": "backend", "title": "后端手册", "url": "https://example.com/backend"},
    ],
    "specs": [],
    "abilities": [{"name": "语音唤醒", "input": "麦克风", "compute": "device", "output": "唤醒", "offline": "断网可用", "sourceIds": ["source"]}],
    "parts": [
        {"id": "mcu", "name": "主控", "mpn": "ESP32-S3", "manufacturer": "乐鑫", "role": "采集音频", "status": "observed", "sourceIds": ["source"]},
        {"id": "board", "name": "显示板", "mpn": "UNKNOWN-PART", "status": "unknown", "sourceIds": []},
    ],
    "build": {
        "repo": "https://example.com/source",
        "steps": ["核对板型", "配置后端", "试装外壳"],
        "stepSourceIds": [["board"], ["backend"], []],
        "note": "编辑复现计划，尚待实物验证。",
    },
}
OWNER = {"Authorization": "Bearer 938f73af-88fc-424c-a7b6-b92ff29d1602"}
OTHER = {"Authorization": "Bearer b50dc462-8b4e-4b38-a73d-8941518aaf94"}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)
        env = patch.dict("os.environ", {
            "ATLAS_AI_BASE_URL": "",
            "ATLAS_AI_KEY": "",
            "ATLAS_AI_MODEL": "",
            "ATLAS_AI_VISION_MODEL": "",
            "ATLAS_RESEARCH_RUNS_PER_IP_PER_MINUTE": "8",
            "ATLAS_RESEARCH_RUNS_GLOBAL_PER_MINUTE": "60",
            "ATLAS_RESEARCH_MAX_HISTORY": "3000",
            "ATLAS_RESEARCH_MAX_NOTES": "5000",
        })
        env.start()
        self.addCleanup(env.stop)
        self.create_client()

    def create_client(self):
        app = FastAPI()
        app.include_router(create_research_router(self.path, lambda: {"products": [PRODUCT]}), prefix="/api")
        self.app = app
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def configure_model(self):
        with patch.dict("os.environ", {
            "ATLAS_AI_BASE_URL": "https://example.com/v1",
            "ATLAS_AI_KEY": "test-key",
            "ATLAS_AI_MODEL": "test-model",
            "ATLAS_AI_VISION_MODEL": "test-vision-model",
        }):
            self.create_client()

    def run_request(self, **overrides):
        body = {"query": "ESP32-S3", "workflow": "evidence", "productIds": [], "useMemory": False}
        return self.client.post("/api/research/run", headers=OWNER, json={**body, **overrides})

    def test_fallback_uses_only_selected_part_evidence_and_preserves_history(self):
        result = self.run_request(productIds=["example-toy"], partId="mcu")
        self.assertEqual(result.status_code, 200, result.text)
        run = result.json()
        self.assertEqual(run["mode"], "catalog")
        self.assertIn("ESP32-S3", run["answer"])
        self.assertNotIn("UNKNOWN-PART", run["answer"])
        self.assertEqual(run["citations"][0]["url"], "https://example.com/source")
        self.assertEqual(run["productIds"], ["example-toy"])
        history = self.client.get("/api/research/history", headers=OWNER)
        self.assertEqual(history.json()["runs"][0]["id"], run["id"])
        self.assertEqual(self.client.get("/api/research/history", headers=OTHER).json(), {"runs": []})
        self.assertEqual(self.client.get("/api/research/history").status_code, 401)
        self.assertEqual(self.client.delete("/api/research/history", headers=OWNER).status_code, 204)
        self.assertEqual(self.client.get("/api/research/history", headers=OWNER).json(), {"runs": []})

    def test_unknown_query_does_not_fill_with_unrelated_sources(self):
        result = self.run_request(query="无人机飞行高度")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["citations"], [])
        self.assertEqual(result.json()["productIds"], [])

    def test_build_workflow_preserves_exact_step_sources(self):
        response = self.run_request(workflow="build", productIds=["example-toy"])
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertIn("核对板型 [example-toy:board]", result["answer"])
        self.assertIn("配置后端 [example-toy:backend]", result["answer"])
        self.assertIn("试装外壳（编辑建议）", result["answer"])
        self.assertNotIn("配置后端 [example-toy:source]", result["answer"])

    def test_notes_are_isolated_and_owner_can_delete(self):
        note = self.client.post("/api/research/notes", headers=OWNER, json={"text": "关注端侧语音"})
        self.assertEqual(note.status_code, 201, note.text)
        note_id = note.json()["id"]
        path = f"/api/research/notes/{note_id}"
        self.assertEqual(self.client.delete(path, headers=OTHER).status_code, 204)
        self.assertEqual(len(self.client.get("/api/research/notes", headers=OWNER).json()["notes"]), 1)
        self.assertEqual(self.client.delete(path, headers=OWNER).status_code, 204)
        self.assertEqual(self.client.get("/api/research/notes", headers=OWNER).json(), {"notes": []})

    def test_image_needs_explicit_consent_and_is_not_sent_without_provider(self):
        raw = io.BytesIO()
        Image.new("RGB", (8, 8)).save(raw, format="PNG")
        image = "data:image/png;base64," + base64.b64encode(raw.getvalue()).decode("ascii")
        result = self.run_request(query="", image=image, allowImageTransfer=False)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn("同意", result.json()["warning"])
        self.assertNotIn(image, self.client.get("/api/research/history", headers=OWNER).text)
        self.assertEqual(self.run_request(query="", image=image, allowImageTransfer=True).status_code, 200)
        self.assertEqual(self.run_request(query="", image="data:image/png;base64,Z29vZA==").status_code, 422)

    def test_model_citations_are_server_validated_and_notes_require_opt_in(self):
        self.configure_model()
        self.client.post("/api/research/notes", headers=OWNER, json={"text": "关注端侧语音"})
        model_result = {"claims": [{"text": "主控为 ESP32-S3", "citationIds": ["example-toy:source"]}]}
        with patch.object(ModelProvider, "complete", return_value=model_result) as complete:
            self.assertEqual(self.run_request().json()["mode"], "model")
            self.assertNotIn("关注端侧语音", complete.call_args.args[1][1]["content"])
            result = self.run_request(useMemory=True).json()
            self.assertIn("关注端侧语音", complete.call_args.args[1][1]["content"])
            self.assertIn("[example-toy:source]", result["answer"])
            self.assertEqual(result["citations"][0]["url"], "https://example.com/source")
            model_result["claims"][0]["citationIds"] = ["wrong:external"]
            fallback = self.run_request().json()
            self.assertEqual(fallback["mode"], "catalog")
            self.assertNotIn("wrong:external", fallback["answer"])
            self.assertIn("引用校验", fallback["warning"])

    def test_vision_terms_can_find_catalog_and_use_distinct_observation_label(self):
        self.configure_model()
        raw = io.BytesIO()
        Image.new("RGB", (8, 8)).save(raw, format="PNG")
        image = "data:image/png;base64," + base64.b64encode(raw.getvalue()).decode("ascii")
        with patch.object(ModelProvider, "complete", side_effect=[
            {"observation": "可见疑似 ESP32-S3 字样", "terms": ["ESP32-S3"]},
            {"claims": [{"text": "目录有该料号", "citationIds": ["example-toy:source"]}]},
        ]) as complete:
            self.run_request(query="", image=image, allowImageTransfer=False)
            complete.assert_not_called()
            result = self.run_request(query="", image=image, allowImageTransfer=True).json()
            self.assertEqual(result["mode"], "model")
            self.assertEqual(result["productIds"], ["example-toy"])
            self.assertIn("图像观察（候选信息）", result["answer"])
            transmitted = complete.call_args_list[0].args[1][1]["content"][1]["image_url"]["url"]
            self.assertTrue(transmitted.startswith("data:image/jpeg;base64,"))

    def test_limit_by_address_resists_rotating_workspaces_and_forwarded_headers(self):
        with patch.dict("os.environ", {
            "ATLAS_RESEARCH_RUNS_PER_IP_PER_MINUTE": "1",
            "ATLAS_RESEARCH_RUNS_GLOBAL_PER_MINUTE": "2",
        }):
            self.create_client()
        payload = {"query": "ESP32-S3", "workflow": "evidence", "productIds": [], "useMemory": False}
        self.assertEqual(self.run_request().status_code, 200)
        response = self.client.post(
            "/api/research/run", headers={**OTHER, "X-Forwarded-For": "192.0.2.3"}, json=payload,
        )
        self.assertEqual(response.status_code, 429, response.text)
        self.assertIn("Retry-After", response.headers)
        with TestClient(self.app, client=("192.0.2.2", 1234)) as other_client:
            self.assertEqual(other_client.post("/api/research/run", headers=OTHER, json=payload).status_code, 200)
        with TestClient(self.app, client=("192.0.2.3", 1234)) as third_client:
            self.assertEqual(third_client.post("/api/research/run", headers=OTHER, json=payload).status_code, 429)

    def test_global_retention_across_workspaces(self):
        with patch.dict("os.environ", {"ATLAS_RESEARCH_MAX_HISTORY": "1", "ATLAS_RESEARCH_MAX_NOTES": "1"}):
            self.create_client()
        payload = {"query": "ESP32-S3", "workflow": "evidence", "productIds": [], "useMemory": False}
        self.assertEqual(self.run_request().status_code, 200)
        self.assertEqual(self.client.post("/api/research/run", headers=OTHER, json=payload).status_code, 200)
        self.assertEqual(self.client.get("/api/research/history", headers=OWNER).json(), {"runs": []})
        self.assertEqual(len(self.client.get("/api/research/history", headers=OTHER).json()["runs"]), 1)
        self.assertEqual(self.client.post("/api/research/notes", headers=OWNER, json={"text": "先看硬件"}).status_code, 201)
        self.assertEqual(self.client.post("/api/research/notes", headers=OTHER, json={"text": "先看结构"}).status_code, 429)
        self.assertEqual(len(self.client.get("/api/research/notes", headers=OWNER).json()["notes"]), 1)

    def test_invalid_consent_and_payloads_do_not_echo_user_content(self):
        result = self.run_request(allowImageTransfer="true")
        self.assertEqual(result.status_code, 422)
        self.assertNotIn('"input"', result.text)
        oversized_query = "勿回显" * 401
        result = self.run_request(query=oversized_query)
        self.assertEqual(result.status_code, 422)
        self.assertNotIn(oversized_query, result.text)


if __name__ == "__main__":
    unittest.main()
