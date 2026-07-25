"""Normalization rules shared by all ingest paths (live parsers + data_loader).

Mirrors BUILD_SPEC.md section 4.5. Never invent a value: absent -> None,
stated-as-zero -> 0.0. Those are kept distinct throughout.
"""
import re

RAW_FLAG_PHRASES = [
    "外国人相談可",
    "外国人可",
    "国籍不問",
    "保証人不要",
    "保証人不在可",
    "保証会社必須",
    "保証会社利用可",
    "緊急連絡先必須",
    "日本語",
    "留学生可",
    "法人契約",
    "女性限定",
    "二人入居可",
    "事務所利用可",
]

_MAN_YEN_RE = re.compile(r"([\d.]+)\s*万円?")
_YEN_RE = re.compile(r"([\d,]+)\s*円")
_MONTHS_RE = re.compile(r"([\d.]+)\s*(?:ヶ月|か月|カ月)")
_SQM_RE = re.compile(r"([\d.]+)\s*m")
_WALK_RE = re.compile(r"歩\s*(\d+)\s*分")
_WARD_RE = re.compile(r"([^\s0-9０-９]+?[区市])")


def man_yen_to_int(text: str | None) -> int | None:
    """"8.5万円" -> 85000"""
    if not text:
        return None
    m = _MAN_YEN_RE.search(text)
    if not m:
        return None
    return round(float(m.group(1)) * 10000)


def yen_to_int(text: str | None) -> int | None:
    """"15,000円" -> 15000. Returns 0 for explicit "-"/"なし"/"ゼロ", None if absent."""
    if not text:
        return None
    stripped = text.strip()
    if stripped in ("-", "―", "なし", "ゼロ", ""):
        return 0
    m = _YEN_RE.search(stripped)
    if m:
        return int(m.group(1).replace(",", ""))
    # Sometimes fee cells reuse the 万円 format (e.g. deposit shown as "8.5万円")
    return man_yen_to_int(stripped)


def fee_to_months(text: str | None) -> float | None:
    """"礼金2ヶ月" -> 2.0. "-"/"なし"/"ゼロ" -> 0.0. Absent -> None."""
    if not text:
        return None
    stripped = text.strip()
    if stripped in ("-", "―", "なし", "ゼロ", ""):
        return 0.0
    m = _MONTHS_RE.search(stripped)
    if m:
        return float(m.group(1))
    return None


def area_to_sqm(text: str | None) -> float | None:
    if not text:
        return None
    m = _SQM_RE.search(text)
    return float(m.group(1)) if m else None


def walk_minutes(text: str | None) -> int | None:
    if not text:
        return None
    m = _WALK_RE.search(text)
    return int(m.group(1)) if m else None


def normalize_layout(text: str | None) -> str | None:
    """Uppercase, no spaces: "1ldk" / "1 LDK" -> "1LDK"."""
    if not text:
        return None
    return re.sub(r"\s+", "", text).upper()


def extract_ward(address: str | None) -> str | None:
    if not address:
        return None
    m = _WARD_RE.search(address)
    return m.group(1) if m else None


def extract_raw_flags(conditions_text: str | None) -> list[str]:
    """Exact-phrase matches only, per BUILD_SPEC.md 4.5 — never paraphrase."""
    if not conditions_text:
        return []
    return [phrase for phrase in RAW_FLAG_PHRASES if phrase in conditions_text]
