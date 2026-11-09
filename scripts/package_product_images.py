"""Package generated contact sheets into distinct product views and verified spec graphics."""

import argparse
import base64
import json
import subprocess
import unicodedata
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/catalog.json"
SHEETS = ROOT / "runtime/product-image-sheets"
OUTPUT = ROOT / "web/public/assets/product-studies"


def run(*command):
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()


def wrap(value, width):
    line, size = "", 0
    for char in value:
        advance = 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
        if line and size + advance > width:
            yield line.rstrip()
            line, size = "", 0
        line += char
        size += advance
    if line:
        yield line.rstrip()


def svg_text(x, y, value, size, color="#1f2525", weight=500):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(value)}</text>'


def specs_art(product, plate, destination):
    facts = [("品牌", product["brand"])]
    facts.extend((record["label"], record["value"]) for record in product["specs"]
                 if record["key"] != "appearance" and record["sourceIds"])
    if len(facts) < 4:
        facts.extend((record["label"], record["value"]) for record in product["specs"]
                     if record["key"] == "appearance" and record["sourceIds"])
        ability = next((item["name"] for item in product["abilities"] if item["sourceIds"]), None)
        if ability:
            facts.append(("AI 能力", ability))
    name = list(wrap(product["name"], 41))
    art = base64.b64encode(plate.read_bytes()).decode("ascii")
    title = [svg_text(52, 84 + 42*i, line, 40, weight=700) for i, line in enumerate(name)]
    table = []
    y = 210
    for label, value in facts[:7]:
        value_lines = list(wrap(value, 30))
        table.append(f'<path d="M620 {y-25}H1138" stroke="#d8ddda"/>')
        table.append(svg_text(622, y, label, 20, "#546262", 600))
        table.extend(svg_text(784, y + i*24, line, 21) for i, line in enumerate(value_lines))
        y += max(62, len(value_lines) * 24 + 34)
    height = max(800, y+66)
    markup = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" aria-label="{escape(product["name"], quote=True)}硬件规格信息图">',
        f'<rect width="1200" height="{height}" rx="25" fill="#f4f6f3"/>',
        '<rect x="52" y="41" width="29" height="4" fill="#bc542c"/>',
        *title, svg_text(53, 155, "硬件规格  /  HARDWARE SPECIFICATIONS", 22, "#536462", 600),
        '<rect x="50" y="182" width="532" height="420" rx="20" fill="#e8eeeb"/>',
        f'<image href="data:image/webp;base64,{art}" x="58" y="190" width="516" height="404" preserveAspectRatio="xMidYMid meet"/>',
        svg_text(55, 631, "AI 生成配图 · 参数来自档案来源", 19, "#536462"),
        *table,
        svg_text(52, height-30, "硬件志  /  HARDWARE ATLAS", 16, "#536462", 600),
        '</svg>',
    ]
    destination.write_text("".join(markup), encoding="utf-8")


def package(product):
    identifier = product["id"]
    sheet = SHEETS / f"{identifier}.png"
    if not sheet.is_file():
        return False
    w, h = (int(x) for x in run("magick", "identify", "-format", "%w %h", str(sheet)).split())
    if w < 1200 or h < 800:
        raise ValueError(f"Sheet too small: {sheet}")
    half_w, half_h = w // 2, h // 2
    margin = 12
    output = OUTPUT / identifier
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as scratch:
        paths = {}
        for key, column, row in (("overview", 0, 0), ("detail", 1, 0),
                                 ("specs", 0, 1), ("angles", 1, 1)):
            path = Path(scratch) / "specs-art.webp" if key == "specs" else output / f"{key}.webp"
            left, top = column * half_w + margin, row * half_h + margin
            box = f"{half_w-2*margin}x{half_h-2*margin}+{left}+{top}"
            run("magick", str(sheet), "-crop", box, "+repage", "-quality", "89", str(path))
            if key == "specs":
                path = output / "specs.svg"
                specs_art(product, Path(scratch) / "specs-art.webp", path)
            paths[key] = f"/assets/product-studies/{identifier}/{path.name}"
    illustration = product["illustration"]
    if illustration.get("breakdown"):
        paths["overview"] = illustration["panels"]["overview"]
    illustration["panels"] = paths
    source_ids = [*illustration["sourceIds"]]
    source_ids.extend(source for record in product["specs"] for source in record["sourceIds"])
    source_ids.extend(source for item in product["abilities"] for source in item["sourceIds"])
    illustration["sourceIds"] = list(dict.fromkeys(source_ids))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    data = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    missing = [p["id"] for p in data["products"] if not package(p)]
    if args.complete and missing:
        raise SystemExit(f"Missing generated sheets: {', '.join(missing)}")
    temporary = CATALOG.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(CATALOG)
    print(f"Four independent images attached to {len(data['products']) - len(missing)} products.")


if __name__ == "__main__":
    main()
