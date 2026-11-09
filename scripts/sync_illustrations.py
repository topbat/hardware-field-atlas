"""Attach finished ImageGen plates to the catalog, preserving their reference sources."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/catalog.json"
PLATES = ROOT / "web/public/assets/illustrations"
TEARDOWNS = {
    "xiaomi-glasses": "teardown",
    "xiaozhi-esp32": "board",
    "xiaomi-speaker-pro": "teardown-original",
    "sharge-a1": "teardown",
}
CONCEPTS = {"xiaodu-tiantianscreen-2201", "hibianli-hi1000", "9am-up"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--complete", action="store_true", help="Require a plate for every product.")
    args = parser.parse_args()
    data = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    products = data["products"]
    missing = []
    for product in products:
        identifier = product["id"]
        path = PLATES / f"{identifier}.webp"
        if not path.is_file():
            missing.append(identifier)
            continue
        with path.open("rb") as file:
            header = file.read(12)
        if header[:4] != b"RIFF" or header[8:] != b"WEBP":
            raise ValueError(f"Invalid WebP: {path}")
        source_ids = []
        if identifier in TEARDOWNS:
            source_ids.append(TEARDOWNS[identifier])
        for spec in product["specs"]:
            if spec["label"] == "外观与接口":
                source_ids.extend(spec["sourceIds"])
        if image := product.get("image"):
            if image.get("sourceId"):
                source_ids.append(image["sourceId"])
        if not source_ids:
            source_ids.append(product["sources"][0]["id"])
        product["illustration"] = {
            "url": f"/assets/illustrations/{identifier}.webp",
            "technical": "teardown" if identifier in TEARDOWNS else "functional",
            "exterior": "concept" if identifier in CONCEPTS else "reference",
            "sourceIds": list(dict.fromkeys(source_ids)),
        }
    if missing and args.complete:
        raise SystemExit(f"Missing plates: {', '.join(missing)}")
    staging = CATALOG.with_suffix(".json.tmp")
    staging.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staging.replace(CATALOG)
    print(f"Attached {len(products) - len(missing)} of {len(products)} illustration plates.")


if __name__ == "__main__":
    main()
