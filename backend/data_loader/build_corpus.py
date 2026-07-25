"""Ingests backend/data/ur_properties_raw.json (real UR賃貸 data, gathered by
hand/research from ur-net.go.jp) into the fallback corpus listings.sqlite.

Each UR property page states a RANGE of rent/layout/area across its units, not
one specific unit. To avoid inventing a unit that doesn't exist, each property
becomes one row using the property's stated MINIMUM rent and smallest layout
in its range — both real, verbatim numbers from the source — with the full
range preserved in conditions_text so nothing is lost.
"""
import hashlib
import json
import os
from datetime import date, datetime, timezone

from schemas import Listing
from services import corpus
from services.normalize import extract_raw_flags, normalize_layout

RAW_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ur_properties_raw.json")

# Verifiable, general UR policy stated on UR's own site (e.g. the Setagaya area
# page title: "礼金・仲介手数料・更新料・保証人ナシ") — true for all UR properties,
# not an invented per-listing claim.
UR_POLICY_TEXT = (
    "UR賃貸住宅。礼金なし、仲介手数料なし、更新料なし、保証人不要。"
)


def _first_layout(layout_range: str) -> str | None:
    """"1DK〜4LDK" -> "1DK" """
    if not layout_range:
        return None
    first = layout_range.split("〜")[0].split("~")[0].strip()
    return normalize_layout(first)


def _make_id(source_url: str) -> str:
    return "ur_" + hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:16]


def load_ur_properties() -> list[dict]:
    if not os.path.exists(RAW_PATH):
        raise FileNotFoundError(
            f"{RAW_PATH} not found — run the UR data-gathering step first (see MEMORY.md)"
        )
    with open(RAW_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_ur_listing(raw: dict) -> Listing:
    conditions_text = (
        f"{UR_POLICY_TEXT} 賃料{raw['rent_min_jpy']:,}円〜{raw['rent_max_jpy']:,}円、"
        f"間取り{raw['layout_range']}、"
        f"専有面積{raw['area_min_sqm']}㎡〜{raw['area_max_sqm']}㎡。"
    )
    return Listing(
        id=_make_id(raw["source_url"]),
        source="ur",
        source_url=raw["source_url"],
        title=raw["name"],
        address=raw.get("address"),
        ward=raw.get("ward"),
        nearest_station=raw.get("nearest_station"),
        line=raw.get("line"),
        walk_minutes=raw.get("walk_minutes"),
        layout=_first_layout(raw.get("layout_range", "")),
        area_sqm=raw.get("area_min_sqm"),
        rent_jpy=raw["rent_min_jpy"],
        kanrihi_jpy=raw.get("kanrihi_jpy") or 0,
        shikikin_months=0.0,  # UR policy: no key money/deposit-equivalent fees — stated, not invented
        reikin_months=0.0,
        conditions_text=conditions_text,
        raw_flags=extract_raw_flags(conditions_text),
    )


def run() -> int:
    raws = load_ur_properties()
    fetched_at = datetime.now(timezone.utc).date().isoformat()
    count = 0
    for raw in raws:
        listing = build_ur_listing(raw)
        corpus.upsert_listing(listing, fetched_at=fetched_at, raw_blob=raw)
        count += 1
    return count


if __name__ == "__main__":
    n = run()
    print(f"Ingested {n} real UR properties into listings.sqlite ({corpus.count_rows()} total rows)")
