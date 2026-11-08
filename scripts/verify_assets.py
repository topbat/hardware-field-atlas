"""Verify that each browser model and diagram can join to the catalog."""

import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web/public"


def verify_glb(path):
    data = path.read_bytes()
    magic, version, total, json_length, json_type = struct.unpack_from("<4sIII4s", data)
    if (magic, version, total, json_type) != (b"glTF", 2, len(data), b"JSON"):
        raise ValueError(f"Invalid GLB header: {path}")
    model = json.loads(data[20:20 + json_length])
    groups = [node["extras"]["part_id"] for node in model["nodes"]
              if node.get("extras", {}).get("part_id")]
    if not model.get("meshes") or not groups or len(groups) != len(set(groups)):
        raise ValueError(f"Missing meshes or invalid part IDs: {path}")
    return set(groups)


def main():
    catalog = json.loads((ROOT / "data/catalog.json").read_text(encoding="utf-8-sig"))
    checked = 0
    for product in catalog["products"]:
        if not product["model"]:
            continue
        product_id = product["id"]
        groups = verify_glb(PUBLIC / product["model"]["url"].removeprefix("/"))
        svg = ET.parse(PUBLIC / f"assets/diagrams/{product_id}.svg")
        markers = {node.attrib["data-part-id"] for node in svg.iter() if "data-part-id" in node.attrib}
        if markers != groups:
            raise ValueError(f"SVG and GLB IDs differ for {product_id}: {markers ^ groups}")
        known = {part["id"] for part in product["parts"]}
        if groups - known:
            raise ValueError(f"Catalog lacks {groups - known} for {product_id}")
        checked += 1
        print(f"{product_id}: {len(groups)} mapped parts")
    if not checked:
        raise ValueError("No 3D assets in the catalog")


if __name__ == "__main__":
    main()
