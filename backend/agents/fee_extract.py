import logging

from prompts.fee_extract import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from services.fee_extract import extract_chukai_months, extract_koushinryou_months

logger = logging.getLogger(__name__)

_FIELDS = (
    "chukai_months", "koushinryou_months",
    "hoshou_initial_jpy", "hoshou_annual_jpy",
    "kasai_hoken_jpy", "kagi_koukan_jpy",
)


async def extract_real_fees(conditions_text: str | None) -> dict:
    """Returns {field: value_or_None} for every field in _FIELDS — only fields
    the listing actually states, never a fabricated default. Tries ai& first
    (can find fee mentions regex can't, e.g. oddly-phrased or table-formatted
    fees); falls back to regex (services/fee_extract.py, chukai/koushinryou
    only — the other four fields have no reliable regex pattern) when ai&
    isn't configured. A field stays None if neither path finds it — the
    caller must NOT substitute a default, per product policy."""
    fields = {k: None for k in _FIELDS}
    if not conditions_text:
        return fields

    try:
        result = await complete_json("qwen", SYSTEM, conditions_text, SCHEMA_HINT)
        return {**fields, **{k: result.get(k) for k in _FIELDS if result.get(k) is not None}}
    except (AgentError, ProviderNotConfigured) as e:
        logger.info("fee extraction agent unavailable (%s), using regex fallback", e)
        fields["chukai_months"] = extract_chukai_months(conditions_text)
        fields["koushinryou_months"] = extract_koushinryou_months(conditions_text)
        return fields
