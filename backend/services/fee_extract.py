"""Regex-based extraction of real fee values from a listing's conditions_text,
so the Cost Auditor uses what the listing actually states instead of always
falling back to the BUILD_SPEC.md defaults. This is the deterministic fallback
tier — agents/cost.py tries ai& extraction first (agents/fee_extract.py),
then this, then the hardcoded default, in that order.

Only extracts fields with reliably consistent phrasing in real listings
(仲介手数料, 更新料). Guarantor fees, fire insurance, and key-exchange costs
vary too unpredictably in free text to regex safely — those stay assumptions.
"""
import re
import unicodedata

_CHUKAI_RE = re.compile(r"仲介手数料[^。\n]{0,15}?(無料|なし|半額|[\d.]+\s*(?:ヶ月|か月|カ月))")
_KOUSHIN_RE = re.compile(r"更新料[^。\n]{0,15}?(無料|なし|[\d.]+\s*(?:ヶ月|か月|カ月))")


def _to_months(token: str) -> float:
    if token in ("無料", "なし"):
        return 0.0
    if token == "半額":
        return 0.5
    m = re.match(r"([\d.]+)", token)
    return float(m.group(1)) if m else 1.0


def extract_chukai_months(conditions_text: str | None) -> float | None:
    """Returns the real stated agency-fee months if found (e.g. "仲介手数料無料"
    -> 0.0, "仲介手数料【0.55ヶ月分】" -> 0.55), else None (caller should fall
    back to ai& or the default assumption)."""
    if not conditions_text:
        return None
    text = unicodedata.normalize("NFKC", conditions_text)
    m = _CHUKAI_RE.search(text)
    return _to_months(m.group(1)) if m else None


def extract_koushinryou_months(conditions_text: str | None) -> float | None:
    """Returns the real stated renewal-fee months if found, else None."""
    if not conditions_text:
        return None
    text = unicodedata.normalize("NFKC", conditions_text)
    m = _KOUSHIN_RE.search(text)
    return _to_months(m.group(1)) if m else None
