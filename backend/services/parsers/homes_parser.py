"""Parses LIFULL HOME'S chintai ward-listing pages.

Structure confirmed by hand against a real fetch of
https://www.homes.co.jp/chintai/tokyo/shinjuku-city/list/ during spec-writing:
  div[class*="prg-kksBukken"]                 one listing card
    a.prg-detailLink.detailLink[href]          detail URL (absolute)
    span.bukkenName                            building name
    table tr th.price / td.price               "18.87万円 / 15,000円"  (rent / kanrihi)
    table tr th.address / td.address           address
    table tr th.traffic / td.traffic           "JR中央線 中野駅 徒歩4分"
    table tr th.space / td.space               "31.34m² / 1DK"  (area / layout)

HOME'S list pages don't carry fee (敷金/礼金) or eligibility-condition text —
those only live on the detail page, which is fetched lazily per-listing for
the final shortlist (see services/live_search.py::enrich_with_detail),
not for every candidate up front.

If HOME'S changes markup, this raises HomesParseError and the caller treats
it like a network failure — falls back to the other live source or corpus.
"""
import hashlib
import re

from bs4 import BeautifulSoup

from schemas import Listing
from services.normalize import area_to_sqm, extract_ward, man_yen_to_int, normalize_layout, walk_minutes, yen_to_int


class HomesParseError(Exception):
    pass


def _make_id(detail_url: str) -> str:
    return "homes_" + hashlib.sha1(detail_url.encode("utf-8")).hexdigest()[:16]


def _parse_price_cell(text: str | None) -> tuple[int | None, int]:
    """"18.87万円 / 15,000円" -> (188700, 15000). Missing kanrihi -> 0."""
    if not text:
        return None, 0
    rent_part, _, kanrihi_part = text.partition("/")
    rent_jpy = man_yen_to_int(rent_part)
    kanrihi_jpy = yen_to_int(kanrihi_part) or 0
    return rent_jpy, kanrihi_jpy


def _parse_traffic_cell(text: str | None) -> tuple[str | None, str | None, int | None]:
    """"JR中央線 中野駅 徒歩4分" -> (line, station, walk_minutes)."""
    if not text:
        return None, None, None
    walk = walk_minutes(text)
    head = re.split(r"徒歩|歩", text)[0].strip()
    parts = head.rsplit(" ", 1) if " " in head else [head, None]
    if len(parts) == 2:
        line, station = parts[0].strip() or None, parts[1].strip() or None
    else:
        line, station = None, head or None
    return line, station, walk


def _parse_space_cell(text: str | None) -> tuple[float | None, str | None]:
    """"31.34m² / 1DK" -> (31.34, "1DK")."""
    if not text:
        return None, None
    area_part, _, layout_part = text.partition("/")
    return area_to_sqm(area_part), normalize_layout(layout_part)


def parse_homes_ward_page(html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select('div[class*="prg-kksBukken"]')
    if not cards:
        raise HomesParseError("no prg-kksBukken cards found — markup may have changed")

    listings: list[Listing] = []
    for card in cards:
        link_el = card.select_one("a.prg-detailLink.detailLink[href]")
        if link_el is None:
            continue
        detail_url = link_el["href"]

        name_el = card.select_one("span.bukkenName")
        title = name_el.get_text(strip=True) if name_el else "(無題)"

        price_el = card.select_one("td.price")
        address_el = card.select_one("td.address")
        traffic_el = card.select_one("td.traffic")
        space_el = card.select_one("td.space")

        rent_jpy, kanrihi_jpy = _parse_price_cell(price_el.get_text(" ", strip=True) if price_el else None)
        if rent_jpy is None:
            continue  # rent required — skip unparseable card

        address = address_el.get_text(strip=True) if address_el else None
        line, station, walk_min = _parse_traffic_cell(traffic_el.get_text(strip=True) if traffic_el else None)
        area_sqm, layout = _parse_space_cell(space_el.get_text(strip=True) if space_el else None)

        listings.append(
            Listing(
                id=_make_id(detail_url),
                source="homes",
                source_url=detail_url,
                title=title,
                address=address,
                ward=extract_ward(address),
                nearest_station=station,
                line=line,
                walk_minutes=walk_min,
                layout=layout,
                area_sqm=area_sqm,
                floor=None,
                rent_jpy=rent_jpy,
                kanrihi_jpy=kanrihi_jpy,
                shikikin_months=None,
                reikin_months=None,
                conditions_text=None,
                raw_flags=[],
            )
        )
    return listings
