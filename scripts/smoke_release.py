"""Exercise a running release image without any model credentials."""

import json
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def smoke(base):
    def request(path, data=None, headers=None):
        with urlopen(Request(base + path, data=data, headers=headers or {}), timeout=8) as response:
            return response.read(), response.headers.get_content_type()

    for attempt in range(30):
        try:
            assert json.loads(request("/api/health")[0]) == {"status": "ok"}
            break
        except URLError:
            if attempt == 29:
                raise
            time.sleep(1)

    html, content_type = request("/products/xiaomi-glasses?view=illustration")
    assert content_type == "text/html" and b'<div id="root">' in html
    catalog = json.loads(request("/api/catalog?limit=100")[0])
    assert len(catalog["products"]) >= 17
    product = json.loads(request("/api/products/xiaomi-glasses")[0])
    model, _ = request(product["model"]["url"])
    assert model.startswith(b"glTF")
    gallery = product["illustration"]["breakdown"]
    assert len(gallery["details"]) >= 6 and len(gallery["angles"]) >= 3
    for card in (gallery["details"][0], gallery["angles"][0]):
        svg, content_type = request(card["url"])
        assert content_type == "image/svg+xml"
        assert card["title"].encode() in svg and b"data:image/webp;base64," in svg

    headers = {"Authorization": f"Bearer {uuid4()}", "Content-Type": "application/json"}
    run = json.dumps({
        "query": "ESP32-S3", "workflow": "evidence", "productIds": ["xiaozhi-esp32"], "useMemory": False,
    }).encode()
    result = json.loads(request("/api/research/run", run, headers)[0])
    assert result["mode"] == "catalog" and result["citations"]
    history = json.loads(request("/api/research/history", headers=headers)[0])
    assert history["runs"][0]["id"] == result["id"]
    print("Release smoke passed: SPA, catalog, GLB, captioned images, offline research and SQLite history.")


if __name__ == "__main__":
    smoke(sys.argv[1].rstrip("/"))
