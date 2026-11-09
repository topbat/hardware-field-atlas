"""Publish one captioned image per generated detail and view."""

import argparse
import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from package_product_images import run, svg_text, wrap

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/catalog.json"
PUBLIC = ROOT / "web/public"
SHEETS = ROOT / "runtime/visual-breakdown-sheets"
META = ROOT / "docs/product-visual-breakdowns.json"
OUTPUT = PUBLIC / "assets/visual-breakdowns"


def art_dimensions(image):
    return [int(number) for number in run("magick", "identify", "-format", "%w %h", str(image)).split()]


def captioned_card(image, output, product_name, title, caption, kind, concept=False):
    art_w, art_h = art_dimensions(image)
    width = 720
    image_height = round(width * art_h / art_w)
    lines = list(wrap(caption, 54))
    height = image_height + 124 + (len(lines) - 1) * 25
    marker = f"{kind}  /  AI {'概念示意' if concept else '生成示意'}"
    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    body = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#f5f3ee"/>',
        f'<image href="data:image/webp;base64,{encoded}" width="{width}" height="{image_height}"/>',
        f'<path d="M23 {image_height+22}h16" stroke="#bc542c" stroke-width="3"/>',
        svg_text(49, image_height + 27, f"{product_name}  /  {marker}", 16, "#576361", 600),
        svg_text(23, image_height + 64, title, 28, weight=700),
        *(svg_text(24, image_height + 99 + index * 25, line, 24, "#495454")
          for index, line in enumerate(lines)),
        "</svg>",
    ]
    output.write_text("".join(body), encoding="utf-8")


def package(product, spec):
    identifier = product["id"]
    sheet = SHEETS / f"{identifier}.png"
    if not sheet.is_file():
        return False
    directory = OUTPUT / identifier
    directory.mkdir(parents=True, exist_ok=True)
    illustration = product["illustration"]
    part_lookup = {part["id"]: part for part in product["parts"]}
    default_sources = illustration["sourceIds"]
    concept = illustration["exterior"] == "concept"
    detail_rows = spec["details"][identifier]
    rows = 3 if len(detail_rows) == 6 else 2
    cells = [(sheet, rows, index, index < len(detail_rows), row)
             for index, row in enumerate([*detail_rows, *spec["angles"]])]
    supplement = SHEETS / "supplement.png"
    if supplement.is_file():
        for index, (target, title, caption, *ref) in enumerate(spec["supplementalDetails"]):
            if target == identifier:
                cells.append((supplement, 2, index, True, [title, caption, None, *ref]))
    dimensions = {image: art_dimensions(image) for image in {cell[0] for cell in cells}}
    if any(w < 1200 or h < 800 for w, h in dimensions.values()):
        raise ValueError(f"Sheet dimensions invalid: {identifier} {dimensions}")
    images = {"details": [], "angles": []}
    with TemporaryDirectory() as temp:
        for image, row_count, index, detail, row in cells:
            title, caption, _prompt, *ref = row
            w, h = dimensions[image]
            row_idx, col = divmod(index, 3)
            offset = 12
            left, top = round(col * w / 3) + offset, round(row_idx * h / row_count) + offset
            crop_w = round((col + 1) * w / 3) - offset - left
            crop_h = round((row_idx + 1) * h / row_count) - offset - top
            cell = Path(temp) / "cell.webp"
            run("magick", str(image), "-crop", f"{crop_w}x{crop_h}+{left}+{top}",
                "+repage", "-quality", "88", str(cell))
            group = images["details" if detail else "angles"]
            number = len(group) + 1
            name = f"{'detail' if detail else 'angle'}-{number:02d}.svg"
            if not detail:
                caption = spec["angleCaptions"][identifier][number - 1]
                if concept:
                    caption += " 外观未核实，仅为同类设备示意。"
            captioned_card(cell, directory / name, product["name"], title, caption,
                           "部位" if detail else "角度", concept)
            card = {"url": f"/assets/visual-breakdowns/{identifier}/{name}",
                    "title": title, "caption": caption, "sourceIds": default_sources}
            if ref:
                part = part_lookup[ref[0]]
                card["partId"] = part["id"]
                card["sourceIds"] = part["sourceIds"] or default_sources
            group.append(card)
    overview = PUBLIC / f"assets/product-studies/{identifier}/overview.webp"
    captioned_card(overview, directory / "overview.svg", product["name"], "总体图", product["tagline"],
                   "概览", concept)
    illustration["panels"]["overview"] = f"/assets/visual-breakdowns/{identifier}/overview.svg"
    illustration["breakdown"] = images
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    data = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    spec = json.loads(META.read_text(encoding="utf-8-sig"))
    products = data["products"]
    if args.complete:
        names = [product["id"] for product in products] + ["supplement"]
        missing = [name for name in names if not (SHEETS / f"{name}.png").is_file()]
        if missing:
            raise SystemExit(f"Missing source sheets: {', '.join(missing)}")
    packaged = sum(package(product, spec) for product in products)
    staged = CATALOG.with_suffix(".json.tmp")
    staged.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged.replace(CATALOG)
    print(f"Packaged captioned detail and angle galleries for {packaged} products.")


if __name__ == "__main__":
    main()
