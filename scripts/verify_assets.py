"""Verify that each browser model and diagram can join to the catalog."""

import base64
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web/public"
SVG = "{http://www.w3.org/2000/svg}"


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


def verify_card(path, title, caption):
    svg = ET.parse(path).getroot()
    art = svg.find(f"{SVG}image")
    if svg.tag != f"{SVG}svg" or art is None:
        raise ValueError(f"Invalid captioned card: {path}")
    href = art.get("href", "")
    prefix = "data:image/webp;base64,"
    if not href.startswith(prefix):
        raise ValueError(f"No embedded WebP: {path}")
    pixels = base64.b64decode(href[len(prefix):], validate=True)
    if pixels[:4] != b"RIFF" or pixels[8:12] != b"WEBP":
        raise ValueError(f"Invalid embedded WebP: {path}")
    labels = [node.text or "" for node in svg.findall(f"{SVG}text")]
    compact = lambda value: "".join(value.split())
    if title not in labels or compact(caption) not in compact("".join(labels)):
        raise ValueError(f"Missing title or caption: {path}")


def main():
    catalog = json.loads((ROOT / "data/catalog.json").read_text(encoding="utf-8-sig"))
    briefs = json.loads((ROOT / "docs/product-visual-breakdowns.json").read_text(encoding="utf-8"))
    detail_titles = {identifier: [row[0] for row in rows] for identifier, rows in briefs["details"].items()}
    for identifier, title, *_ in briefs["supplementalDetails"]:
        detail_titles[identifier].append(title)
    angle_titles = [row[0] for row in briefs["angles"]]
    card_urls = set()
    checked = 0
    photos = 0
    illustrations = 0
    panel_count = 0
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
            if panels := plate.get("panels"):
                if set(panels) != {"overview", "detail", "specs", "angles"}:
                    raise ValueError(f"Missing product image types: {product_id}")
                for key, url in panels.items():
                    image = PUBLIC / url.removeprefix("/")
                    if key == "overview" and plate.get("breakdown"):
                        verify_card(image, "总体图", product["tagline"])
                    elif key == "specs":
                        svg = ET.parse(image)
                        if svg.getroot().tag != "{http://www.w3.org/2000/svg}svg":
                            raise ValueError(f"Invalid specifications graphic: {image}")
                    else:
                        with image.open("rb") as file:
                            header = file.read(12)
                        if header[:4] != b"RIFF" or header[8:] != b"WEBP":
                            raise ValueError(f"Invalid product WebP: {image}")
                    panel_count += 1
            breakdown = plate.get("breakdown")
            if product_id in detail_titles and not breakdown:
                raise ValueError(f"Missing visual breakdown: {product_id}")
            if breakdown:
                parts = {part["id"] for part in product["parts"]}
                for kind, expected in (("details", detail_titles[product_id]), ("angles", angle_titles)):
                    if [card["title"] for card in breakdown[kind]] != expected:
                        raise ValueError(f"Incomplete {kind} gallery: {product_id}")
                    for card in breakdown[kind]:
                        url = card["url"]
                        if url in card_urls or not card["sourceIds"] or set(card["sourceIds"]) - sources:
                            raise ValueError(f"Repeated or unsourced card: {url}")
                        if card.get("partId") and card["partId"] not in parts:
                            raise ValueError(f"Unknown part on card: {url}")
                        verify_card(PUBLIC / url.removeprefix("/"), card["title"], card["caption"])
                        card_urls.add(url)
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
    print(f"{len(card_urls)} unique captioned detail and angle cards verified")
    print(f"{photos} product image references linked to sources")
    print(f"{illustrations} sourced illustration plates verified; {panel_count} independent product images")


if __name__ == "__main__":
    main()
