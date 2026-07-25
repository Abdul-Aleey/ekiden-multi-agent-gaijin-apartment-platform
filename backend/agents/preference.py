import logging
import re

from prompts.preference import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from schemas import SearchPreferences

logger = logging.getLogger(__name__)


async def extract_preferences(message: str, prior: SearchPreferences | None) -> SearchPreferences:
    """Extract structured preferences from free text. Degrades to a best-effort
    manual parse if ai& isn't configured yet (see providers/registry.py) —
    the orchestrator must still be able to proceed for local dev/demo."""
    prior_json = prior.model_dump_json() if prior else "null"
    user = f"Prior known preferences (may be partially filled): {prior_json}\n\nUser message: {message}"

    try:
        result = await complete_json("qwen", SYSTEM, user, SCHEMA_HINT)
        return SearchPreferences(**result)
    except (AgentError, ProviderNotConfigured) as e:
        logger.warning("preference agent unavailable (%s), using naive fallback parse", e)
        return _naive_fallback(message, prior)


_BUDGET_MAN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*万\s*円?")
_BUDGET_YEN_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{5,})\s*(?:yen|円|jpy)?", re.IGNORECASE)
_LAYOUT_RE = re.compile(r"\b([1-9][SLDK]{1,4})\b", re.IGNORECASE)


def _extract_budget(message: str) -> int | None:
    """Explicit numbers the user actually typed — regex extraction, not invention."""
    m = _BUDGET_MAN_RE.search(message)
    if m:
        return round(float(m.group(1)) * 10000)
    m = _BUDGET_YEN_RE.search(message)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _extract_layouts(message: str) -> list[str]:
    """All layout tokens mentioned — "1K or 1DK" must keep both, not just the first match."""
    return [m.upper() for m in dict.fromkeys(_LAYOUT_RE.findall(message))]


def _naive_fallback(message: str, prior: SearchPreferences | None) -> SearchPreferences:
    """Simple regex-based extraction, only used when ai& isn't configured yet.
    Only pulls values the user explicitly typed — never invents or estimates."""
    from services.area_slugs import resolve_area

    area = resolve_area(message)
    area_label = area.label if area else (prior.area_or_ward if prior else None)
    budget = _extract_budget(message) or (prior.max_budget_jpy if prior else None)
    layouts = _extract_layouts(message) or (prior.layouts if prior else [])

    missing = []
    if not area_label:
        missing.append("area_or_ward")
    if budget is None:
        missing.append("max_budget_jpy")

    return SearchPreferences(
        area_or_ward=area_label,
        max_budget_jpy=budget,
        layouts=layouts,
        must_haves=prior.must_haves if prior else [],
        missing_critical_fields=missing,
    )
