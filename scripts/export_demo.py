"""Export the validated public catalog and BOM downloads for GitHub Pages."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from atlas.main import create_app


def export(output: Path):
    bom = output / "bom"
    bom.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as state:
        with TestClient(create_app(seed_path=ROOT / "data/catalog.json", data_dir=Path(state),
                                   web_dist=output, research=False)) as client:
            response = client.get("/api/catalog", params={"limit": 200})
            response.raise_for_status()
            catalog = response.json()
            if catalog["total"] != len(catalog["products"]):
                raise ValueError("Online demo catalog export would omit products.")
            (output / "catalog.json").write_bytes(response.content)
            for product in catalog["products"]:
                product_id = product["id"]
                response = client.get(f"/api/products/{product_id}/bom.csv")
                response.raise_for_status()
                (bom / f"{product_id}.csv").write_bytes(response.content)
            print(f"Exported {catalog['total']} public product records and BOM files.")


if __name__ == "__main__":
    export(Path(sys.argv[1]))
