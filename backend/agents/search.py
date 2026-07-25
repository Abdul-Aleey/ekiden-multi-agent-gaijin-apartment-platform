import logging

from agents.area_resolve import resolve_area_llm
from prompts.search import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from schemas import Listing, SearchPreferences
from services import corpus
from services.dedup import dedupe_listings
from services.live_search import LiveSearchError, ProgressCallback, search_live

logger = logging.getLogger(__name__)

MAX_CANDIDATES_TO_RANK = 30
SHORTLIST_SIZE = 8


async def find_candidates(
    prefs: SearchPreferences, on_progress: ProgressCallback = None
) -> tuple[list[Listing], str, str]:
    """Returns (candidates, source_status, area_resolution). source_status is
    one of: "live_both", "live_homes_only", "live_suumo_only", "fallback",
    "no_data". area_resolution is "model", "fallback", or "none" — see
    agents/area_resolve.py; surfaced so the UI can show whether the location
    match came from real model reasoning or the dictionary fallback.

    Live search covers all of Japan (prefecture-level everywhere, ward-level
    precision for Tokyo's 23 wards). The local fallback corpus is Tokyo-only
    real data — if live fails outside Tokyo, there's no fallback to show, so
    that's reported honestly as "no_data" rather than silently substituting
    Tokyo listings for a different area."""
    area, area_resolution = await resolve_area_llm(prefs.area_or_ward)

    listings: list[Listing] = []
    status = "no_data"
    if area:
        try:
            live_listings, status = await search_live(area, on_progress=on_progress)
            listings.extend(live_listings)
        except LiveSearchError as e:
            logger.warning("live search failed for both sites: %s", e)

    # UR properties are real, matching-relevant candidates — not just a
    # last-resort fallback. Merge any that match this search's ward/budget
    # into the real candidate pool (Tokyo only, since the UR corpus is
    # Tokyo-only) so a genuinely good UR match competes for a real shortlist
    # card with its own true cost and eligibility read, instead of being
    # relegated to an unfiltered "alternatives" footnote that may not even
    # match what the user asked for.
    if area and area.prefecture_ja == "東京都":
        ur_matches = corpus.query_fallback(ward_ja=area.ward_ja, max_budget_jpy=prefs.max_budget_jpy, limit=20)
        listings.extend(ur_matches)
        if status == "no_data" and ur_matches:
            status = "fallback"

    if not listings:
        return [], "no_data", area_resolution

    return dedupe_listings(_apply_filters(listings, prefs)), status, area_resolution


def _apply_filters(listings: list[Listing], prefs: SearchPreferences) -> list[Listing]:
    filtered = listings
    if prefs.max_budget_jpy:
        filtered = [l for l in filtered if l.rent_jpy <= prefs.max_budget_jpy]
    if prefs.layouts:
        filtered = [l for l in filtered if l.layout in prefs.layouts]
    if prefs.max_walk_minutes:
        filtered = [
            l for l in filtered if l.walk_minutes is None or l.walk_minutes <= prefs.max_walk_minutes
        ]
    if len(filtered) >= SHORTLIST_SIZE or len(filtered) == len(listings):
        return filtered
    # A narrow budget/layout can legitimately leave only 1-2 exact matches —
    # per product requirement, the shortlist should still reach SHORTLIST_SIZE
    # whenever the raw pool has enough listings, backfilled with the
    # next-closest candidates rather than showing a near-empty shortlist.
    # Exact matches still rank first later via _guarantee_exact_matches_first,
    # so a backfilled listing can never outrank one that satisfies every
    # stated constraint.
    remaining = [l for l in listings if l not in filtered]
    remaining.sort(key=lambda l: _violation_count(l, prefs))
    return filtered + remaining[: SHORTLIST_SIZE - len(filtered)]


_MAX_REASON_CHARS = 60


def _trim_reason(text: str) -> str:
    """Defensive cap even though the prompt asks for <50 chars — a card slot
    is small and a long reason just gets clipped mid-thought otherwise."""
    text = text.strip()
    return text if len(text) <= _MAX_REASON_CHARS else text[: _MAX_REASON_CHARS - 1].rstrip() + "…"


def _violation_count(l: Listing, prefs: SearchPreferences) -> int:
    """0 = satisfies every explicitly stated hard constraint; higher = more
    violated. Used as a stable pre-sort key AFTER ranking (by either the
    model or the naive fallback) so a listing that violates a stated
    constraint can never outrank one that satisfies all of them — the
    ranking model still decides relative order *within* each tier, this
    just guarantees exact matches always lead."""
    violations = 0
    if prefs.layouts and l.layout not in prefs.layouts:
        violations += 1
    if prefs.max_budget_jpy and l.rent_jpy > prefs.max_budget_jpy:
        violations += 1
    if prefs.max_walk_minutes and l.walk_minutes is not None and l.walk_minutes > prefs.max_walk_minutes:
        violations += 1
    return violations


def _guarantee_exact_matches_first(
    ranked: list[tuple[Listing, str]], prefs: SearchPreferences
) -> list[tuple[Listing, str]]:
    # Stable sort: only reorders across violation-count tiers, never within one.
    return sorted(ranked, key=lambda pair: _violation_count(pair[0], prefs))


async def rank_shortlist(
    candidates: list[Listing], prefs: SearchPreferences, lang: str = "en"
) -> list[tuple[Listing, str]]:
    """Returns up to SHORTLIST_SIZE (listing, match_reason) pairs, best first.
    Degrades to a naive budget/layout-distance sort if ai& isn't configured."""
    pool = candidates[:MAX_CANDIDATES_TO_RANK]
    if not pool:
        return []

    try:
        candidate_json = [
            {
                "id": l.id,
                "title": l.title,
                "ward": l.ward,
                "nearest_station": l.nearest_station,
                "layout": l.layout,
                "area_sqm": l.area_sqm,
                "rent_jpy": l.rent_jpy,
                "kanrihi_jpy": l.kanrihi_jpy,
            }
            for l in pool
        ]
        user = (
            f"Response language for match_reason: {lang}\n\n"
            f"Preferences: {prefs.model_dump_json()}\n\nCandidates: {candidate_json}"
        )
        result = await complete_json("qwen", SYSTEM, user, SCHEMA_HINT)
        by_id = {l.id: l for l in pool}
        ranked = []
        for item in result.get("ranked", [])[:SHORTLIST_SIZE]:
            listing = by_id.get(item.get("id"))
            if listing is not None:
                ranked.append((listing, _trim_reason(item.get("match_reason", ""))))
        if ranked:
            return _guarantee_exact_matches_first(ranked, prefs)
    except (AgentError, ProviderNotConfigured) as e:
        logger.warning("search rank agent unavailable (%s), using naive sort", e)

    return _guarantee_exact_matches_first(_naive_rank(pool, prefs, lang), prefs)


def _naive_rank(pool: list[Listing], prefs: SearchPreferences, lang: str = "en") -> list[tuple[Listing, str]]:
    def score(l: Listing) -> float:
        s = 0.0
        if prefs.max_budget_jpy:
            s += abs(l.rent_jpy - prefs.max_budget_jpy) / 1000
        if prefs.layouts and l.layout not in prefs.layouts:
            s += 50
        return s

    reason = "予算・間取り・エリアの条件に一致" if lang == "ja" else "Matched on ward/budget/layout filters"
    ranked = sorted(pool, key=score)[:SHORTLIST_SIZE]
    return [(l, reason) for l in ranked]
