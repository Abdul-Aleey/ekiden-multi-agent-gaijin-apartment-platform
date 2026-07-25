import logging

from prompts.trust import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from schemas import Listing, TrustReport
from services.benchmarks import ward_layout_median

logger = logging.getLogger(__name__)


async def check_trust(listing: Listing, lang: str = "en") -> TrustReport:
    """Independent model (GMI), deliberately different from ai& (used for
    search/eligibility) — see BUILD_SPEC.md section 8.4. GMI isn't configured
    yet, so this currently falls back to ai&'s fast tier (still a real model
    call, just loses the "independent vendor" property until GMI is set up)
    before finally degrading to a deterministic rule-based check if no LLM
    is reachable at all."""
    median = ward_layout_median(listing.ward, listing.layout)
    record = {
        "title": listing.title,
        "address": listing.address,
        "rent_jpy": listing.rent_jpy,
        "layout": listing.layout,
        "ward_layout_median_rent_jpy": median,
        "shikikin_months": listing.shikikin_months,
        "reikin_months": listing.reikin_months,
        "posted_date": listing.posted_date,
        "source_url": listing.source_url,
    }
    user = f"Response language for explanation_en: {lang}\n\n{record}"

    try:
        result = await complete_json("gmi", SYSTEM, user, SCHEMA_HINT)
        return TrustReport(listing_id=listing.id, **result)
    except (AgentError, ProviderNotConfigured) as e:
        logger.info("GMI unavailable (%s), trying ai& fast tier instead", e)
        try:
            result = await complete_json("aiand_fast", SYSTEM, user, SCHEMA_HINT)
            return TrustReport(listing_id=listing.id, **result)
        except (AgentError, ProviderNotConfigured) as e2:
            logger.warning("ai& fast tier also unavailable (%s), using rule-based fallback", e2)
            return _rule_based_fallback(listing, median, lang)


def _rule_based_fallback(listing: Listing, median: int | None, lang: str = "en") -> TrustReport:
    from schemas import TrustSignal

    ja = lang == "ja"
    signals = []
    if median and listing.rent_jpy < median * 0.6:
        signals.append(
            TrustSignal(
                code="price_outlier",
                severity="high",
                explanation_en="この間取りの区内相場より家賃がかなり低くなっています。" if ja
                else "Rent is well below the ward/layout median for comparable units.",
                evidence=f"rent {listing.rent_jpy} vs ward median {median} for {listing.layout}",
            )
        )
    if listing.shikikin_months is None and listing.reikin_months is None:
        signals.append(
            TrustSignal(
                code="missing_fees",
                severity="medium",
                explanation_en="敷金・礼金の情報が記載されていません。" if ja
                else "No shikikin/reikin information is stated for this listing.",
                evidence="shikikin_months and reikin_months are both null",
            )
        )
    if not listing.address or len(listing.address) < 6:
        signals.append(
            TrustSignal(
                code="vague_address",
                severity="low",
                explanation_en="住所に番地・建物名が記載されていません。" if ja
                else "Address lacks a specific block/building number.",
                evidence=f"address field: '{listing.address}'",
            )
        )

    high_count = sum(1 for s in signals if s.severity == "high")
    risk = "high_risk" if high_count >= 2 else ("caution" if signals else "clear")
    return TrustReport(listing_id=listing.id, risk=risk, signals=signals)
