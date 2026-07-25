import datetime
import logging

from prompts.strategy_advisor import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from schemas import CostBreakdown, EligibilityReport, Listing, StrategyAdvice, TrustReport

logger = logging.getLogger(__name__)


async def advise_strategy(
    listing: Listing,
    cost: CostBreakdown,
    trust: TrustReport,
    eligibility: EligibilityReport,
    lang: str = "en",
) -> StrategyAdvice:
    """Listing-specific negotiation + screening-presentation plan. Tries GMI
    first (per the playbook this was modeled on — pins the Strategy Advisor
    to GMI Cloud specifically), then ai&'s quality tier as a second real-model
    attempt (same "always prefer a real model over a template" pattern as
    trust.py), and only falls back to the deterministic playbook below if
    neither is reachable."""
    record = {
        "rent_jpy": listing.rent_jpy,
        "reikin_months": listing.reikin_months,
        "building_year": listing.building_year,
        "cost_breakdown": cost.model_dump(),
        "trust_risk": trust.risk,
        "trust_signals": [s.model_dump() for s in trust.signals],
        "eligibility_outlook": eligibility.outlook,
        "eligibility_findings": [f.model_dump() for f in eligibility.findings],
    }
    user = f"Response language: {lang}\n\n{record}"

    for provider in ("gmi", "aiand_quality"):
        try:
            result = await complete_json(provider, SYSTEM, user, SCHEMA_HINT)
            return StrategyAdvice(listing_id=listing.id, plan=result.get("plan", ""))
        except (AgentError, ProviderNotConfigured) as e:
            logger.info("strategy advisor: %s unavailable (%s)", provider, e)

    return StrategyAdvice(listing_id=listing.id, plan=_template_plan(listing, eligibility, lang))


def _template_plan(listing: Listing, eligibility: EligibilityReport, lang: str) -> str:
    ja = lang == "ja"
    tips: list[str] = []

    building_age = (
        datetime.date.today().year - listing.building_year if listing.building_year else None
    )
    if listing.reikin_months and listing.reikin_months > 0:
        if building_age is not None and building_age >= 15:
            tips.append(
                f"この建物は築{building_age}年です。礼金（{listing.reikin_months}ヶ月）の減額・免除を"
                "交渉してみましょう — 築年数のある物件は応じてもらえることが多いです。"
                if ja else
                f"The building is {building_age} years old — ask the agency to waive or reduce the "
                f"{listing.reikin_months}-month reikin; older stock is often flexible on this."
            )
        else:
            tips.append(
                f"礼金は{listing.reikin_months}ヶ月です。一度交渉してみる価値はありますが、"
                "築浅物件では応じてもらえないことが多いです。"
                if ja else
                f"Reikin here is {listing.reikin_months} month(s) — worth asking once, but newer "
                "buildings rarely move on this."
            )

    tips.append(
        "仲介手数料は法律上「賃料1ヶ月分＋税」が上限です。契約前に0.5ヶ月への減額を相談してみましょう。"
        if ja else
        "Agency fees are legally capped at 1 month's rent plus tax in Japan, and sometimes negotiable "
        "down to 0.5 months — ask before signing, never after."
    )

    if eligibility.outlook != "likely":
        tips.append(
            "審査に不安要素がある場合は、初回連絡時に家賃の2〜3ヶ月分の前払いや、外国籍対応の保証会社を"
            "利用可能である旨を伝え、懸念を先回りして解消しましょう。"
            if ja else
            "Since eligibility isn't a clear \"likely\" here, preempt screening concerns in your first "
            "message: offer 2-3 months' rent prepaid and mention you can use a guarantor company that "
            "accepts foreign nationals."
        )

    return ("\n".join(f"・{t}" for t in tips)) if ja else ("\n".join(f"- {t}" for t in tips))
