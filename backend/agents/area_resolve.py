import logging

from prompts.area_resolve import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from services.area_slugs import PREFECTURE_ROMAJI, TOKYO_WARD_ROMAJI, ResolvedArea, resolve_area

logger = logging.getLogger(__name__)


async def resolve_area_llm(area_text: str | None) -> tuple[ResolvedArea | None, str]:
    """Resolves free text to a searchable Japanese area. Returns (area, method)
    where method is "model" (qwen understood it, including casual/fuzzy
    references a dictionary lookup can't), "fallback" (dictionary/regex match
    in services/area_slugs.py — used when the model isn't configured or fails),
    or "none" (neither could identify a place). The frontend surfaces `method`
    so it's visible whether a search used real model reasoning or the fallback,
    per product requirement: never silently hide which path served the user."""
    if not area_text:
        return None, "none"

    try:
        result = await complete_json("qwen", SYSTEM, area_text, SCHEMA_HINT)
        prefecture_ja = result.get("prefecture_ja")
        ward_ja = result.get("ward_ja")
        if prefecture_ja in PREFECTURE_ROMAJI:
            if prefecture_ja == "東京都" and ward_ja in TOKYO_WARD_ROMAJI:
                return ResolvedArea(prefecture_ja=prefecture_ja, prefecture_romaji="tokyo", ward_ja=ward_ja), "model"
            return ResolvedArea(prefecture_ja=prefecture_ja, prefecture_romaji=PREFECTURE_ROMAJI[prefecture_ja]), "model"
        # Model ran but didn't confidently identify a real place — try the
        # dictionary fallback before giving up, in case it's an exact known name.
    except (AgentError, ProviderNotConfigured) as e:
        logger.info("area resolution model unavailable (%s), using dictionary fallback", e)

    area = resolve_area(area_text)
    return (area, "fallback") if area else (None, "none")
