"""Cross-source dedup, per BUILD_SPEC.md section 4.2.

Two sites listing the same physical unit is the norm (agencies cross-post).
Groups by a fuzzy key and keeps the richest record per group, merging
raw_flags from all sources in the group.
"""
import re
import unicodedata

from schemas import Listing

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_name(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)  # full-width -> half-width, etc.
    return _WHITESPACE_RE.sub("", text).lower()


def _fuzzy_key(listing: Listing) -> tuple:
    name_key = _normalize_name(listing.title)
    rent_bucket = round(listing.rent_jpy / 1000) if listing.rent_jpy else None
    if name_key:
        return (name_key, rent_bucket, listing.layout, listing.floor)
    # No usable building name — fall back to ward/station/rent/layout.
    return (
        listing.ward,
        listing.nearest_station,
        round(listing.rent_jpy / 2000) * 2000 if listing.rent_jpy else None,
        listing.layout,
    )


def dedupe_listings(listings: list[Listing]) -> list[Listing]:
    groups: dict[tuple, list[Listing]] = {}
    for listing in listings:
        groups.setdefault(_fuzzy_key(listing), []).append(listing)

    deduped: list[Listing] = []
    for group in groups.values():
        if len(group) == 1:
            deduped.append(group[0])
            continue

        def richness(l: Listing) -> int:
            return len(l.conditions_text or "")

        # Prefer live-sourced over fallback-corpus when both present; among ties,
        # richer conditions_text wins since that drives the eligibility read.
        best = sorted(
            group,
            key=lambda l: (l.source in ("homes", "suumo"), richness(l)),
            reverse=True,
        )[0]

        merged_flags = sorted({flag for l in group for flag in l.raw_flags})
        deduped.append(best.model_copy(update={"raw_flags": merged_flags}))

    return deduped
