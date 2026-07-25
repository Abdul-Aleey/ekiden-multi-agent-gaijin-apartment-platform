import logging

from prompts.translate import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from services.romanize import romanize_listing_fields, romanize_text

logger = logging.getLogger(__name__)


async def localize_fields(fields: dict[str, str | None], lang: str) -> dict[str, str | None]:
    """Translates a dict of {field_name: Japanese text} into English when
    lang=="en". Tries ai& for fluent translation first; falls back to
    pykakasi phonetic romanization (services/romanize.py) if ai& isn't
    configured or fails. Returns the input unchanged when lang=="ja"."""
    if lang != "en":
        return fields

    non_empty = {k: v for k, v in fields.items() if v}
    if not non_empty:
        return fields

    try:
        result = await complete_json("qwen", SYSTEM, str(non_empty), SCHEMA_HINT)
        return {**fields, **{k: result.get(k, v) for k, v in non_empty.items()}}
    except (AgentError, ProviderNotConfigured) as e:
        logger.info("translate agent unavailable (%s), using pykakasi romanization fallback", e)
        return {**fields, **{k: romanize_text(v) for k, v in non_empty.items()}}


async def localize_listing_fields(
    title: str | None, address: str | None, ward: str | None,
    nearest_station: str | None, line: str | None, floor: str | None,
    lang: str,
) -> dict:
    """Same purpose as services.romanize.romanize_listing_fields, but tries
    fluent ai& translation first, falling back to that function's pykakasi
    logic (which already handles address/station/line suffix splitting and
    the floor "5F" convention better than a naive translate call would)."""
    if lang != "en":
        return {
            "title": title, "address": address, "ward": ward,
            "nearest_station": nearest_station, "line": line, "floor": floor,
        }

    fallback = romanize_listing_fields(title, address, ward, nearest_station, line, floor)
    fields = {"title": title, "address": address, "nearest_station": nearest_station, "line": line}
    try:
        result = await complete_json("qwen", SYSTEM, str({k: v for k, v in fields.items() if v}), SCHEMA_HINT)
        return {
            "title": result.get("title") or fallback["title"],
            "address": result.get("address") or fallback["address"],
            "ward": fallback["ward"],  # short, formulaic — pykakasi handles this fine, save the tokens
            "nearest_station": result.get("nearest_station") or fallback["nearest_station"],
            "line": result.get("line") or fallback["line"],
            "floor": fallback["floor"],
        }
    except (AgentError, ProviderNotConfigured) as e:
        logger.info("translate agent unavailable (%s), using pykakasi romanization fallback", e)
        return fallback
