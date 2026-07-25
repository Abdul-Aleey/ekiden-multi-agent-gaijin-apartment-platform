import logging

from prompts.followup import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from schemas import ListingCard

logger = logging.getLogger(__name__)


async def answer_followup(card: ListingCard, question: str, lang: str = "en") -> str:
    user = (
        f"Response language: {lang}\n\n"
        f"Listing card data: {card.model_dump_json()}\n\nQuestion: {question}"
    )
    try:
        result = await complete_json("qwen", SYSTEM, user, SCHEMA_HINT)
        return result.get("answer", "")
    except (AgentError, ProviderNotConfigured) as e:
        logger.warning("followup agent unavailable (%s)", e)
        return (
            "Follow-up Q&A isn't available right now (LLM provider not configured). "
            "Please check the listing details above directly."
        )
