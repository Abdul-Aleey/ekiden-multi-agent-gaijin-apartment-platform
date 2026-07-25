"""Live fetch against HOME'S + SUUMO, per BUILD_SPEC.md section 4.1.

Runs both sites concurrently for a ward. If BOTH fail (network error, timeout,
zero parseable cards), raises LiveSearchError so the orchestrator falls back
to the local corpus (services/corpus.py). If only one succeeds, its results
are used and the gap is recorded as an assumption.

Detail-page enrichment (conditions_text, raw_flags) is fetched lazily, only
for the final ranked shortlist — not for every candidate — to keep the list
fetch fast and stay within the search timeout budget.
"""
import asyncio
import logging
import re
from typing import Callable, Optional

import httpx
from bs4 import BeautifulSoup

from config import LIVE_SEARCH_TIMEOUT_S, LIVE_SEARCH_USER_AGENT
from schemas import Listing
from services.area_slugs import ResolvedArea, homes_url, suumo_url
from services.normalize import extract_raw_flags
from services.parsers.homes_parser import parse_homes_ward_page
from services.parsers.suumo_parser import SuumoParseError, parse_suumo_ward_page

logger = logging.getLogger(__name__)

# Matches a clean top-level city/ward page link, e.g. "/chintai/fukuoka/sc_fukuokashihakata/"
# — deliberately anchored at the end so it excludes nested filtered pages like
# ".../sc_fukuokashihakata/mansion/" or ".../sc_x/oz_.../".
_SUUMO_CITY_LINK_RE = re.compile(r'href="(/chintai/[a-z0-9]+/sc_[a-z0-9]+/)"')
MAX_SUUMO_CITY_DRILLDOWN = 4


class LiveSearchError(Exception):
    """Both live sources failed — caller should fall back to the local corpus."""


async def _fetch(url: str, timeout_s: float) -> str:
    async with httpx.AsyncClient(
        headers={"User-Agent": LIVE_SEARCH_USER_AGENT}, timeout=timeout_s, follow_redirects=True
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


ProgressCallback = Optional[Callable[[dict], None]]


def _report(on_progress: ProgressCallback, **data) -> None:
    if on_progress is not None:
        on_progress(data)


async def search_homes_live(
    area: ResolvedArea, timeout_s: float = LIVE_SEARCH_TIMEOUT_S, on_progress: ProgressCallback = None
) -> list[Listing]:
    _report(on_progress, site="HOME'S", status="fetching")
    html = await _fetch(homes_url(area), timeout_s)
    listings = parse_homes_ward_page(html)
    _report(on_progress, site="HOME'S", status="done", count=len(listings))
    return listings


def _discover_suumo_city_urls(html: str, limit: int = MAX_SUUMO_CITY_DRILLDOWN) -> list[str]:
    seen: list[str] = []
    for path in _SUUMO_CITY_LINK_RE.findall(html):
        url = f"https://suumo.jp{path}"
        if url not in seen:
            seen.append(url)
        if len(seen) >= limit:
            break
    return seen


async def search_suumo_live(
    area: ResolvedArea, timeout_s: float = LIVE_SEARCH_TIMEOUT_S, on_progress: ProgressCallback = None
) -> list[Listing]:
    """SUUMO's ward-level pages (Tokyo's 23 special wards) show a listing grid
    directly. Its PREFECTURE-level root, used for every other prefecture,
    is instead a city/ward selector page with zero listings — confirmed by
    testing against Fukuoka during spec work. When that happens (and only for
    non-precise/non-Tokyo areas — a real ward-page failure should still raise),
    discover the real city/ward sub-pages linked from that selector and fetch
    several of them concurrently, merging their listings, so non-Tokyo areas
    still get real multi-city coverage instead of zero SUUMO results."""
    _report(on_progress, site="SUUMO", status="fetching")
    html = await _fetch(suumo_url(area), timeout_s)
    try:
        listings = parse_suumo_ward_page(html)
        _report(on_progress, site="SUUMO", status="done", count=len(listings))
        return listings
    except SuumoParseError:
        if area.is_precise:
            raise
        city_urls = _discover_suumo_city_urls(html)
        if not city_urls:
            raise
        logger.info("SUUMO prefecture root for %s was a selector page, drilling into %d cities", area.label, len(city_urls))
        _report(on_progress, site="SUUMO", status="expanding", cities=len(city_urls))

        tasks = [asyncio.create_task(_fetch(u, timeout_s)) for u in city_urls]
        listings: list[Listing] = []
        for finished in asyncio.as_completed(tasks):
            try:
                page = await finished
                listings.extend(parse_suumo_ward_page(page))
            except (httpx.HTTPError, SuumoParseError):
                continue
            _report(on_progress, site="SUUMO", status="fetching", count=len(listings))

        if not listings:
            raise SuumoParseError(f"no listings found in any of {len(city_urls)} discovered city pages for {area.label}")
        _report(on_progress, site="SUUMO", status="done", count=len(listings))
        return listings


async def _with_one_retry(coro_fn, *args, **kwargs) -> list[Listing]:
    try:
        return await coro_fn(*args, **kwargs)
    except Exception as first_error:  # noqa: BLE001 — deliberately broad, see docstring
        logger.warning("live search first attempt failed for %s: %s", coro_fn.__name__, first_error)
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as second_error:  # noqa: BLE001
            logger.warning("live search retry failed for %s: %s", coro_fn.__name__, second_error)
            raise second_error


async def search_live(
    area: ResolvedArea, timeout_s: float = LIVE_SEARCH_TIMEOUT_S, on_progress: ProgressCallback = None
) -> tuple[list[Listing], str]:
    """Returns (listings, source_status). source_status is one of:
    "live_both", "live_homes_only", "live_suumo_only". Raises LiveSearchError
    if both sites fail — caller falls back to the corpus (Tokyo only) or
    reports "no_data" for everywhere else in Japan."""
    results = await asyncio.gather(
        _with_one_retry(search_homes_live, area, timeout_s, on_progress=on_progress),
        _with_one_retry(search_suumo_live, area, timeout_s, on_progress=on_progress),
        return_exceptions=True,
    )
    homes_result, suumo_result = results
    homes_ok = isinstance(homes_result, list)
    suumo_ok = isinstance(suumo_result, list)

    if not homes_ok and not suumo_ok:
        raise LiveSearchError(
            f"both HOME'S ({homes_result}) and SUUMO ({suumo_result}) failed for {area.label}"
        )

    merged: list[Listing] = []
    if homes_ok:
        merged.extend(homes_result)
    if suumo_ok:
        merged.extend(suumo_result)

    if homes_ok and suumo_ok:
        status = "live_both"
    elif homes_ok:
        status = "live_homes_only"
    else:
        status = "live_suumo_only"
    return merged, status


async def enrich_with_detail(listing: Listing, timeout_s: float = LIVE_SEARCH_TIMEOUT_S) -> Listing:
    """Fetch a listing's own detail page and fill in conditions_text + raw_flags.
    Best-effort: on any failure, returns the listing unchanged rather than raising —
    a sparse listing is weaker for eligibility but must not blank the whole card."""
    if not listing.source_url:
        return listing
    try:
        html = await _fetch(listing.source_url, timeout_s)
    except Exception as e:  # noqa: BLE001
        logger.info("detail enrichment skipped for %s: %s", listing.id, e)
        return listing

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    full_text = soup.get_text("\n", strip=True)
    conditions_text = full_text[:4000]  # cap length; the flag/keyword match doesn't need the whole page
    return listing.model_copy(
        update={
            "conditions_text": conditions_text,
            "raw_flags": extract_raw_flags(conditions_text),
        }
    )


async def enrich_shortlist(listings: list[Listing], timeout_s: float = LIVE_SEARCH_TIMEOUT_S) -> list[Listing]:
    """Enrich only the final shortlist, concurrently — not the full candidate pool."""
    enriched = await asyncio.gather(*(enrich_with_detail(l, timeout_s) for l in listings))
    return list(enriched)
