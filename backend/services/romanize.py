"""Romanizes display-only listing fields (title, address, ward, station, line)
for English-mode UI, using pykakasi (offline, no API key needed).

This is display-layer only — never applied to conditions_text/quoted_line
(the eligibility "verbatim substring" rule requires the original Japanese)
or to `ward` before it's used to look up benchmarks.json (keyed by Japanese
ward names). Callers must romanize a display copy AFTER analysis, not the
listing object used for matching/benchmarks.
"""
import re
import unicodedata

import pykakasi

_kks = pykakasi.kakasi()

# Administrative/transit suffix characters. kakasi's per-character dictionary
# lookup doesn't reliably find word boundaries in a full address string (e.g.
# "東京都新宿区" comes back as one fused "Toukyoutoshinjukuku"), so we split
# on these ourselves first and romanize each segment independently.
_ADDRESS_SUFFIXES = {
    "都": "-to", "道": "-do", "府": "-fu", "県": "-ken",
    "市": "-shi", "区": "-ku", "町": "-cho", "村": "-son", "郡": "-gun",
}
_TRANSIT_SUFFIXES = {"駅": " Station", "線": " Line"}


def _romanize_word(text: str) -> str:
    """Plain word/phrase romanization, no suffix splitting."""
    # Fullwidth Latin letters (e.g. "ＬＩＢＲ") are common in Japanese listing
    # titles. kakasi treats each fullwidth character as its own token and
    # inserts a space between every letter ("L I B R"). NFKC normalizes
    # fullwidth alphanumerics/punctuation to standard halfwidth first so
    # already-Latin text passes through untouched.
    text = unicodedata.normalize("NFKC", text)
    words = []
    for item in _kks.convert(text):
        hepburn = item["hepburn"].strip()
        if hepburn:
            words.append(hepburn[0].upper() + hepburn[1:])
    return re.sub(r"\s+", " ", " ".join(words)).strip()


def _split_and_romanize(text: str, suffixes: dict[str, str], attach: bool) -> str:
    """Splits `text` right after any character in `suffixes`, romanizes each
    segment on its own (so kakasi can't fuse across the boundary), then
    reassembles with the given English suffix — attached with a hyphen
    (attach=True, for administrative units) or as a separate word
    (attach=False, for "Station"/"Line")."""
    pieces, buf = [], ""
    for ch in text:
        buf += ch
        if ch in suffixes:
            pieces.append(buf)
            buf = ""
    if buf:
        pieces.append(buf)

    out = []
    for piece in pieces:
        last = piece[-1]
        if last in suffixes:
            body = _romanize_word(piece[:-1])
            suffix = suffixes[last]
            out.append(f"{body}{suffix}" if attach else f"{body}{suffix}")
        else:
            out.append(_romanize_word(piece))
    return " ".join(p for p in out if p).strip()


def romanize_text(text: str | None) -> str | None:
    if not text:
        return None
    return _romanize_word(text) or text


_FLOOR_RE = re.compile(r"^(\d+)\s*階$")


def romanize_floor(text: str | None) -> str | None:
    if not text:
        return None
    m = _FLOOR_RE.match(text.strip())
    if m:
        return f"{m.group(1)}F"
    return romanize_text(text)


def romanize_address(text: str | None) -> str | None:
    if not text:
        return None
    return _split_and_romanize(text, _ADDRESS_SUFFIXES, attach=True) or text


def romanize_station_or_line(text: str | None) -> str | None:
    if not text:
        return None
    return _split_and_romanize(text, _TRANSIT_SUFFIXES, attach=False) or text


def romanize_listing_fields(
    title: str | None, address: str | None, ward: str | None,
    nearest_station: str | None, line: str | None, floor: str | None,
) -> dict:
    """Returns a dict of romanized display values — does not touch conditions_text,
    raw_flags, ward (as used for matching), or any other field."""
    return {
        "title": romanize_text(title),
        "address": romanize_address(address),
        "ward": romanize_address(ward),
        "nearest_station": romanize_station_or_line(nearest_station),
        "line": romanize_station_or_line(line),
        "floor": romanize_floor(floor),
    }
