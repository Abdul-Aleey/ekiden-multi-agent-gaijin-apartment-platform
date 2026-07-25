import logging

from prompts.inquiry import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from schemas import ApplicantProfile, EligibilityReport, InquiryEmail, Listing

logger = logging.getLogger(__name__)


async def write_inquiry(
    listing: Listing, profile: ApplicantProfile, eligibility: EligibilityReport
) -> InquiryEmail:
    """ai& — Japanese-hosted generation, since this carries visa/income data
    (BUILD_SPEC.md section 8.8)."""
    top_concern = next(
        (f for f in eligibility.findings if f.verdict in ("concern", "blocker")), None
    )
    user = (
        f"Listing: {listing.title}, {listing.address}, {listing.layout}, "
        f"rent {listing.rent_jpy} yen/month\n"
        f"Applicant household size: {profile.household_size}\n"
        f"Top eligibility concern to address proactively: "
        f"{top_concern.requirement_en + ' - ' + top_concern.advice_en if top_concern else 'none'}"
    )

    try:
        result = await complete_json("aiand_quality", SYSTEM, user, SCHEMA_HINT)
        return InquiryEmail(listing_id=listing.id, **result)
    except (AgentError, ProviderNotConfigured) as e:
        logger.warning("inquiry agent unavailable (%s), returning template fallback", e)
        return _template_fallback(listing, profile)


def _template_fallback(listing: Listing, profile: ApplicantProfile) -> InquiryEmail:
    body = (
        f"拝啓\n\n貴社ウェブサイトにて「{listing.title}」の物件情報を拝見し、"
        f"内見を希望しご連絡いたしました。入居希望人数は{profile.household_size}名です。"
        f"ご都合の良い日程をお知らせいただけますと幸いです。\n\n敬具"
    )
    gloss = (
        f"A polite inquiry expressing interest in viewing '{listing.title}', stating a household "
        f"size of {profile.household_size}, and asking for available viewing dates. "
        f"(Template fallback — ai& provider not yet configured.)"
    )
    return InquiryEmail(
        listing_id=listing.id,
        subject_ja=f"「{listing.title}」内見希望のご連絡",
        body_ja=body,
        body_en_gloss=gloss,
    )
