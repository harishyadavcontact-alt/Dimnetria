#!/usr/bin/env python3
"""Build placeholder static layer artifacts for MVP tile caching."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import BASE_DATE, COUNTRIES, METRICS_BY_COUNTRY
from app.scoring import rrfi_for_country

OUT_DIR = Path("tiles_cache")


def write_country_rrfi_baseline() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    rows = []
    for iso3, c in COUNTRIES.items():
        summary = rrfi_for_country(iso3)
        rows.append(
            {
                "iso3": iso3,
                "name": c["name"],
                "date": str(BASE_DATE),
                "rrfi": summary.rrfi.final_score,
                "water": METRICS_BY_COUNTRY[iso3]["water_security"],
                "food": METRICS_BY_COUNTRY[iso3]["food_self_reliance"],
                "debt": 100 - METRICS_BY_COUNTRY[iso3]["debt_burden"],
                "military": METRICS_BY_COUNTRY[iso3]["military_autonomy"],
            }
        )

    (OUT_DIR / "country_layer_baseline.json").write_text(json.dumps(rows, indent=2))


def main() -> None:
    write_country_rrfi_baseline()
    print(f"Wrote baseline cache to {OUT_DIR}")


if __name__ == "__main__":
    main()
