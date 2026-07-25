"""Parses SUUMO chintai ward-listing pages.

Structure confirmed by hand against a real fetch of
https://suumo.jp/chintai/tokyo/sc_shinjuku/ during spec-writing:
  ul.l-cassetteitem > li > div.cassetteitem   (one building per card)
    .cassetteitem_content-title              building name
    .cassetteitem_detail-col1                address
    .cassetteitem_detail-col2 .cassetteitem_detail-text   station access lines (multiple)
    table.cassetteitem_other tbody tr.js-cassette_link    one row per unit
      td (3rd)  floor
      .cassetteitem_price--rent / --administration        rent / kanrihi
      .cassetteitem_price--deposit / --gratuity            shikikin / reikin
      .cassetteitem_madori / .cassetteitem_menseki          layout / area
      a.js-cassette_link_href[href]                         detail URL (relative)

If SUUMO changes markup, this raises SuumoParseError and the caller
(services/live_search.py) treats it the same as a network failure — falls
back to the other live source or the local corpus.
"""
import hashlib

from bs4 import BeautifulSoup

from schemas import Listing
from services.normalize import (
    area_to_sqm,
    extract_ward,
    fee_to_months,
    man_yen_to_int,
    normalize_layout,
    walk_minutes,
    yen_to_int,
)


def _fee_months(cell_text: str | None, rent_jpy: int) -> float | None:
    """Deposit/gratuity cells show either "1ヶ月", a yen amount like "8.5万円", or "-".
    Prefer the stated months; fall back to yen-amount / rent when only yen is given."""
    months = fee_to_months(cell_text)
    if months is not None:
        return months
    yen = man_yen_to_int(cell_text)
    if yen is not None and rent_jpy:
        return round(yen / rent_jpy, 2)
    return None

BASE_URL = "https://suumo.jp"


class SuumoParseError(Exception):
    pass


def _make_id(detail_url: str) -> str:
    return "suumo_" + hashlib.sha1(detail_url.encode("utf-8")).hexdigest()[:16]


def _parse_station_lines(detail_col2) -> tuple[str | None, str | None, int | None]:
    texts = [el.get_text(strip=True) for el in detail_col2.select(".cassetteitem_detail-text")]
    if not texts:
        return None, None, None
    first = texts[0]
    line, _, rest = first.partition("/")
    station, _, _ = rest.partition("歩")
    return (line.strip() or None), (station.strip() or None), walk_minutes(first)


def parse_suumo_ward_page(html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    buildings = soup.select("div.cassetteitem")
    if not buildings:
        raise SuumoParseError("no .cassetteitem elements found — markup may have changed")

    listings: list[Listing] = []
    for building in buildings:
        title_el = building.select_one(".cassetteitem_content-title")
        address_el = building.select_one(".cassetteitem_detail-col1")
        col2_el = building.select_one(".cassetteitem_detail-col2")
        title = title_el.get_text(strip=True) if title_el else None
        address = address_el.get_text(strip=True) if address_el else None
        line, station, walk_min = (None, None, None)
        if col2_el is not None:
            line, station, walk_min = _parse_station_lines(col2_el)

        for row in building.select("table.cassetteitem_other tbody tr"):
            link_el = row.select_one("a.js-cassette_link_href[href]")
            if link_el is None:
                continue
            detail_url = BASE_URL + link_el["href"] if link_el["href"].startswith("/") else link_el["href"]

            rent_el = row.select_one(".cassetteitem_price--rent")
            kanrihi_el = row.select_one(".cassetteitem_price--administration")
            deposit_el = row.select_one(".cassetteitem_price--deposit")
            gratuity_el = row.select_one(".cassetteitem_price--gratuity")
            madori_el = row.select_one(".cassetteitem_madori")
            menseki_el = row.select_one(".cassetteitem_menseki")
            floor_tds = row.find_all("td")
            floor = floor_tds[2].get_text(strip=True) if len(floor_tds) > 2 else None

            rent_jpy = man_yen_to_int(rent_el.get_text(strip=True) if rent_el else None)
            if rent_jpy is None:
                continue  # rent is required by the schema — skip unparseable rows

            deposit_text = deposit_el.get_text(strip=True) if deposit_el else None
            gratuity_text = gratuity_el.get_text(strip=True) if gratuity_el else None

            listings.append(
                Listing(
                    id=_make_id(detail_url),
                    source="suumo",
                    source_url=detail_url,
                    title=title or "(無題)",
                    address=address,
                    ward=extract_ward(address),
                    nearest_station=station,
                    line=line,
                    walk_minutes=walk_min,
                    layout=normalize_layout(madori_el.get_text(strip=True) if madori_el else None),
                    area_sqm=area_to_sqm(menseki_el.get_text(strip=True) if menseki_el else None),
                    floor=floor,
                    rent_jpy=rent_jpy,
                    kanrihi_jpy=yen_to_int(kanrihi_el.get_text(strip=True) if kanrihi_el else None) or 0,
                    shikikin_months=_fee_months(deposit_text, rent_jpy),
                    reikin_months=_fee_months(gratuity_text, rent_jpy),
                    conditions_text=None,
                    raw_flags=[],
                )
            )
    return listings
