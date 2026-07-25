import asyncio
import time
from typing import AsyncIterator

from agents import cost as cost_agent
from agents import eligibility as eligibility_agent
from agents import preference as preference_agent
from agents import search as search_agent
from agents import strategy_advisor
from agents import translate as translate_agent
from agents import trust as trust_agent
from schemas import ApplicantProfile, CostBreakdown, EligibilityReport, Listing, ListingCard, SearchPreferences, TrustReport
from services.live_search import enrich_shortlist

MAX_CLARIFICATION_ROUNDS = 2


async def _display_listing_dict(listing: Listing, lang: str) -> dict:
    """Listing dict for SSE payloads. In English mode, localizes the
    display-only fields (title/address/ward/station/line/floor) via
    agents/translate.py (ai& if configured, pykakasi romanization
    otherwise) — never mutates the Listing object itself, since `ward` must
    stay Japanese for benchmarks.json lookups and conditions_text must stay
    verbatim Japanese for the eligibility quoted_line rule. Computed once per
    listing and reused for both the `shortlist` and `card` SSE events so a
    listing's displayed fields don't flip back to Japanese between events."""
    data = listing.model_dump()
    if lang == "en":
        data.update(await translate_agent.localize_listing_fields(
            listing.title, listing.address, listing.ward,
            listing.nearest_station, listing.line, listing.floor, lang,
        ))
    return data


def _clarifying_question(missing: list[str], lang: str = "en") -> str:
    if lang == "ja":
        parts = []
        if "area_or_ward" in missing:
            parts.append("お住まいになりたい都道府県・市区町村")
        if "max_budget_jpy" in missing:
            parts.append("ご希望の家賃上限")
        return "・".join(parts) + "を教えていただけますか？"
    parts = []
    if "area_or_ward" in missing:
        parts.append("which area of Japan you'd like to live in (any prefecture or city)")
    if "max_budget_jpy" in missing:
        parts.append("your maximum monthly budget")
    return "Could you tell me " + " and ".join(parts) + "?"


_MAX_ITEM_CHARS = 60  # a card pro/con line — full detail always lives in ListingDetail, this is just the headline


def _trim(text: str, max_chars: int = _MAX_ITEM_CHARS) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def _build_pros_cons(cost: CostBreakdown, trust: TrustReport, eligibility: EligibilityReport) -> tuple[list[str], list[str]]:
    """Deterministic merge — no extra agent call, per BUILD_SPEC.md section 8.6.
    Kept short and headline-only on purpose: these render in a small card slot
    (see ShortlistCard.tsx), and the full reasoning — including the verbatim
    quoted evidence line — is always available one click away in
    ListingDetail.tsx. Cramming the whole quote in here just gets clipped."""
    pros, cons = [], []

    if cost.markup_percent <= 20:
        pros.append(f"True cost only {cost.markup_percent:.0f}% above advertised rent")
    elif cost.markup_percent >= 60:
        cons.append(f"True cost is {cost.markup_percent:.0f}% above advertised rent")

    if trust.risk == "clear":
        pros.append("No bait-listing signals found")
    elif trust.risk == "high_risk":
        cons.append("Multiple trust signals — review carefully")
    for signal in trust.signals:
        if signal.severity == "high":
            cons.append(_trim(signal.explanation_en))

    if eligibility.outlook == "likely":
        pros.append("Eligibility looks favorable")
    for finding in eligibility.findings:
        if finding.verdict == "blocker":
            cons.append(_trim(finding.requirement_en))
        elif finding.verdict == "pass":
            pros.append(_trim(finding.requirement_en))

    return pros, cons


async def _build_card(
    listing: Listing, profile: ApplicantProfile, match_reason: str, lang: str = "en"
) -> ListingCard:
    cost, trust, eligibility = await asyncio.gather(
        cost_agent.audit_cost(listing),
        trust_agent.check_trust(listing, lang),
        eligibility_agent.assess_eligibility(listing, profile, lang),
    )
    # Runs after the three above rather than inside that gather — it needs
    # their output (undisclosed fees, trust signals, eligibility concerns) to
    # ground a listing-specific plan instead of giving generic advice.
    strategy = await strategy_advisor.advise_strategy(listing, cost, trust, eligibility, lang)
    pros, cons = _build_pros_cons(cost, trust, eligibility)
    return ListingCard(
        listing=listing, cost=cost, trust=trust, eligibility=eligibility, strategy=strategy,
        pros=pros, cons=cons, match_reason=match_reason,
    )


async def run_chat_turn(
    message: str,
    profile: ApplicantProfile,
    prior_prefs: SearchPreferences | None,
    clarification_round: int = 0,
    lang: str = "en",
) -> AsyncIterator[tuple[str, dict]]:
    """Yields (event_name, data) tuples matching the SSE contract in
    BUILD_SPEC.md section 6, plus a "card" event per listing carrying the
    full merged ListingCard (a practical addition for the frontend)."""
    start = time.monotonic()

    yield "stage", {"stage": "preferences", "status": "running"}
    prefs = await preference_agent.extract_preferences(message, prior_prefs)

    if prefs.missing_critical_fields and clarification_round < MAX_CLARIFICATION_ROUNDS:
        yield "clarify", {
            "question": _clarifying_question(prefs.missing_critical_fields, lang),
            "prefs": prefs.model_dump(),
        }
        return

    yield "stage", {"stage": "search", "status": "running"}

    # Live progress ("N listings found so far...") while find_candidates runs
    # as a background task — without this the search stage's live-fetch and
    # SUUMO city-drilldown (see services/live_search.py) can take 30-60s+ with
    # nothing visible, looking frozen even though real work is happening.
    progress_queue: asyncio.Queue = asyncio.Queue()
    find_task = asyncio.create_task(
        search_agent.find_candidates(prefs, on_progress=progress_queue.put_nowait)
    )
    while not find_task.done():
        try:
            update = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
            yield "search_progress", update
        except asyncio.TimeoutError:
            continue
    while not progress_queue.empty():
        yield "search_progress", progress_queue.get_nowait()

    candidates, source_status, area_resolution = await find_task
    ranked = await search_agent.rank_shortlist(candidates, prefs, lang)

    # Enrich only the sites that lack conditions_text from their list page (homes/suumo).
    to_enrich = [listing for listing, _ in ranked if listing.source in ("homes", "suumo") and not listing.conditions_text]
    if to_enrich:
        enriched = await enrich_shortlist(to_enrich)
        enriched_by_id = {l.id: l for l in enriched}
        ranked = [(enriched_by_id.get(l.id, l), reason) for l, reason in ranked]

    display_listings = await asyncio.gather(*(_display_listing_dict(l, lang) for l, _ in ranked))
    display_by_id = {d["id"]: d for d in display_listings}

    yield "shortlist", {
        "source_status": source_status,
        "area_resolution": area_resolution,
        "listings": [
            {**display_by_id[listing.id], "match_reason": reason} for listing, reason in ranked
        ],
    }

    if not ranked:
        yield "done", {"elapsed_ms": round((time.monotonic() - start) * 1000)}
        return

    # Stream each listing's card the moment IT finishes, rather than waiting
    # for the slowest one — asyncio.gather (the previous approach here) only
    # returns once every task is done, so all 10 cards' events used to land
    # in the same instant after the longest-running listing completed. That's
    # exactly the "single blob after 40s demos badly" failure BUILD_SPEC.md
    # warns about; asyncio.as_completed yields each task in finish order.
    async def _build_card_tagged(listing: Listing, reason: str):
        try:
            return listing, reason, await _build_card(listing, profile, reason, lang), None
        except Exception as e:  # noqa: BLE001 — surfaced as a per-listing "error" event below
            return listing, reason, None, e

    tasks = [asyncio.create_task(_build_card_tagged(listing, reason)) for listing, reason in ranked]
    for finished in asyncio.as_completed(tasks):
        listing, _reason, card, err = await finished
        if err is not None:
            yield "error", {"stage": "card", "listing_id": listing.id, "message": str(err)}
            continue
        yield "cost", {"listing_id": listing.id, **card.cost.model_dump()}
        yield "trust", {"listing_id": listing.id, **card.trust.model_dump()}
        yield "eligibility", {"listing_id": listing.id, **card.eligibility.model_dump()}
        yield "strategy", {"listing_id": listing.id, **card.strategy.model_dump()}
        card_dict = card.model_dump()
        card_dict["listing"] = display_by_id[listing.id]
        yield "card", card_dict

    yield "done", {"elapsed_ms": round((time.monotonic() - start) * 1000)}
