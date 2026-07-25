"""Read-only access to the local fallback corpus (listings.sqlite).

Used only when live search fails for both sites (see services/live_search.py
and BUILD_SPEC.md section 4). Built/populated by data_loader/, never written
to at request time.
"""
import json
import sqlite3
from contextlib import contextmanager

from config import CORPUS_DB_PATH
from schemas import Listing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_url TEXT,
    fetched_at TEXT NOT NULL,
    title TEXT,
    address TEXT,
    ward TEXT,
    nearest_station TEXT,
    line TEXT,
    walk_minutes INTEGER,
    layout TEXT,
    area_sqm REAL,
    building_year INTEGER,
    floor TEXT,
    rent_jpy INTEGER NOT NULL,
    kanrihi_jpy INTEGER DEFAULT 0,
    shikikin_months REAL,
    reikin_months REAL,
    hoshou_gaisha_required INTEGER,
    conditions_text TEXT,
    raw_flags TEXT,
    posted_date TEXT,
    raw_blob TEXT
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(CORPUS_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def _row_to_listing(row: sqlite3.Row) -> Listing:
    return Listing(
        id=row["id"],
        source=row["source"],
        source_url=row["source_url"],
        title=row["title"] or "(無題)",
        address=row["address"],
        ward=row["ward"],
        nearest_station=row["nearest_station"],
        line=row["line"],
        walk_minutes=row["walk_minutes"],
        layout=row["layout"],
        area_sqm=row["area_sqm"],
        building_year=row["building_year"],
        floor=row["floor"],
        rent_jpy=row["rent_jpy"],
        kanrihi_jpy=row["kanrihi_jpy"] or 0,
        shikikin_months=row["shikikin_months"],
        reikin_months=row["reikin_months"],
        conditions_text=row["conditions_text"],
        raw_flags=json.loads(row["raw_flags"]) if row["raw_flags"] else [],
        posted_date=row["posted_date"],
    )


def query_fallback(
    ward_ja: str | None = None,
    max_budget_jpy: int | None = None,
    layout: str | None = None,
    limit: int = 50,
) -> list[Listing]:
    ensure_schema()
    clauses, params = [], []
    if ward_ja:
        clauses.append("ward = ?")
        params.append(ward_ja)
    if max_budget_jpy:
        clauses.append("rent_jpy <= ?")
        params.append(max_budget_jpy)
    if layout:
        clauses.append("layout = ?")
        params.append(layout)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM listings {where} ORDER BY rent_jpy ASC LIMIT ?"
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_listing(r) for r in rows]


def upsert_listing(listing: Listing, fetched_at: str, raw_blob: dict) -> None:
    ensure_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO listings (
                id, source, source_url, fetched_at, title, address, ward,
                nearest_station, line, walk_minutes, layout, area_sqm,
                building_year, floor, rent_jpy, kanrihi_jpy, shikikin_months,
                reikin_months, conditions_text, raw_flags, posted_date, raw_blob
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_url=excluded.source_url, fetched_at=excluded.fetched_at,
                title=excluded.title, address=excluded.address, ward=excluded.ward,
                nearest_station=excluded.nearest_station, line=excluded.line,
                walk_minutes=excluded.walk_minutes, layout=excluded.layout,
                area_sqm=excluded.area_sqm, building_year=excluded.building_year,
                floor=excluded.floor, rent_jpy=excluded.rent_jpy,
                kanrihi_jpy=excluded.kanrihi_jpy, shikikin_months=excluded.shikikin_months,
                reikin_months=excluded.reikin_months, conditions_text=excluded.conditions_text,
                raw_flags=excluded.raw_flags, posted_date=excluded.posted_date,
                raw_blob=excluded.raw_blob
            """,
            (
                listing.id, listing.source, listing.source_url, fetched_at, listing.title,
                listing.address, listing.ward, listing.nearest_station, listing.line,
                listing.walk_minutes, listing.layout, listing.area_sqm, listing.building_year,
                listing.floor, listing.rent_jpy, listing.kanrihi_jpy, listing.shikikin_months,
                listing.reikin_months, listing.conditions_text, json.dumps(listing.raw_flags, ensure_ascii=False),
                listing.posted_date, json.dumps(raw_blob, ensure_ascii=False),
            ),
        )
        conn.commit()


def count_rows() -> int:
    ensure_schema()
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
