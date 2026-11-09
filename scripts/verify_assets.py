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
    photos = 0
    illustrations = 0
    for product in catalog["products"]:
        product_id = product["id"]
        sources = {source["id"] for source in product["sources"]}
        images = [product.get("image"), *product.get("photos", [])]
        for image in filter(None, images):
            if image["type"] != "concept":
                if image.get("sourceId") not in sources:
                    raise ValueError(f"Image evidence missing for {product_id}")
                photos += 1
        if cutaway := product.get("cutaway"):
            path = PUBLIC / cutaway["url"].removeprefix("/")
            with path.open("rb") as file:
                header = file.read(12)
            if header[:4] != b"RIFF" or header[8:] != b"WEBP":
                raise ValueError(f"Expected a WebP cutaway: {path}")
            if not cutaway["sourceIds"] or set(cutaway["sourceIds"]) - sources:
                raise ValueError(f"Cutaway evidence missing for {product_id}")
        if plate := product.get("illustration"):
            path = PUBLIC / plate["url"].removeprefix("/")
            with path.open("rb") as file:
                header = file.read(12)
            if header[:4] != b"RIFF" or header[8:] != b"WEBP":
                raise ValueError(f"Expected a WebP illustration: {path}")
            if not plate["sourceIds"] or set(plate["sourceIds"]) - sources:
                raise ValueError(f"Illustration evidence missing for {product_id}")
            illustrations += 1
        if not product["model"]:
            continue
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
    print(f"{photos} product image references linked to sources")
    print(f"{illustrations} sourced illustration plates verified")


if __name__ == "__main__":
    main()
