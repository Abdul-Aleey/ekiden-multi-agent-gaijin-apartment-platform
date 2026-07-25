"""Loads benchmarks.json — real ward rent context from MLIT / Tokyo Metropolitan
Government statistics (BUILD_SPEC.md section 4.3). Read-only, built by data_loader."""
import json
import os

from config import BENCHMARKS_PATH

_cache: dict | None = None


def load_benchmarks() -> dict:
    global _cache
    if _cache is None:
        if os.path.exists(BENCHMARKS_PATH):
            with open(BENCHMARKS_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
        else:
            _cache = {"generated_at": None, "wards": {}}
    return _cache


def ward_layout_median(ward_ja: str | None, layout: str | None) -> int | None:
    if not ward_ja or not layout:
        return None
    ward_data = load_benchmarks().get("wards", {}).get(ward_ja)
    if not ward_data:
        return None
    layout_data = ward_data.get("rent_by_layout", {}).get(layout)
    return layout_data.get("median") if layout_data else None
