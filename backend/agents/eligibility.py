import asyncio
import json
import logging
import re

from agents.translate import localize_fields
from prompts.eligibility import SCHEMA_HINT, SYSTEM
from providers.client import AgentError, complete_json
from providers.registry import ProviderNotConfigured
from schemas import ApplicantProfile, EligibilityFinding, EligibilityReport, Listing

logger = logging.getLogger(__name__)

_EN_PAREN_RE = re.compile(r"[（(]([A-Za-z][A-Za-z0-9 .,&'-]*)[）)]")

CONFIDENCE_NOTE = (
    "Based only on what this listing states. Individual landlords may apply "
    "conditions not published here."
)


async def _load_guarantor_alternatives(lang: str = "en") -> list[dict]:
    """Guarantor companies are a genuine "alternative path" — they solve a
    requirement, they aren't an apartment. UR properties used to be listed
    here too, but that was a flat, unfiltered top-5 from the corpus with no
    check that they actually matched the user's search — confusing and often
    irrelevant. Real UR matches now compete as actual shortlist cards instead
    (see agents/search.py::find_candidates), so this only returns guarantor
    companies."""
    import os

    from config import GUARANTOR_COMPANIES_PATH

    guarantor_alts = []
    if os.path.exists(GUARANTOR_COMPANIES_PATH):
        with open(GUARANTOR_COMPANIES_PATH, encoding="utf-8") as f:
            companies = json.load(f)
        guarantor_alts = [
            {
                "kind": "guarantor_company",
                "name": c["name"],
                "why_en": c.get("notes", ""),
                "url": c.get("source_url"),
            }
            for c in companies
            if c.get("accepts_foreign_nationals")
        ]

    if lang == "en":
        # Guarantor company names already carry a real English name in fullwidth
        # parens in the source data (e.g. "日本セーフティー株式会社（Nihon Safety）")
        # — extract that rather than translating, since it's the company's own
        # stated English name, not a guess. Their `notes` text mixes English
        # prose with quoted Japanese terms for authenticity (real company site
        # text) — that part genuinely needs translation, so it goes through
        # the same model-backed localize_fields the rest of the app uses
        # (aiand_fast, falling back to pykakasi) rather than a regex strip.
        localized_notes = await asyncio.gather(*(localize_fields({"why_en": a["why_en"]}, lang) for a in guarantor_alts))
        guarantor_alts = [
            {
                **a,
                "name": (_EN_PAREN_RE.search(a["name"]).group(1) if _EN_PAREN_RE.search(a["name"]) else a["name"]),
                "why_en": loc["why_en"],
            }
            for a, loc in zip(guarantor_alts, localized_notes)
        ]
    return guarantor_alts


async def assess_eligibility(
    listing: Listing, profile: ApplicantProfile, lang: str = "en"
) -> EligibilityReport:
    if not listing.conditions_text:
        return EligibilityReport(
            listing_id=listing.id,
            outlook="uncertain",
            confidence_note="This listing's conditions text wasn't available, so no eligibility "
            "findings could be grounded in verbatim source text. " + CONFIDENCE_NOTE,
            findings=[],
            alternatives=_alternatives_as_models(await _load_guarantor_alternatives(lang)),
        )

    guarantor_alts = await _load_guarantor_alternatives(lang)
    user = (
        f"Response language for requirement_en/advice_en/confidence_note: {lang}\n\n"
        f"Listing conditions_text: {listing.conditions_text}\n\n"
        f"Applicant profile: {profile.model_dump_json()}\n\n"
        f"guarantor_alternatives: {json.dumps(guarantor_alts, ensure_ascii=False)}"
    )

    try:
        result = await complete_json("aiand_quality", SYSTEM, user, SCHEMA_HINT)
        report = EligibilityReport(listing_id=listing.id, **result)
        return _validate_quotes(report, listing.conditions_text)
    except (AgentError, ProviderNotConfigured) as e:
        logger.warning("eligibility agent unavailable (%s), returning conservative default", e)
        return EligibilityReport(
            listing_id=listing.id,
            outlook="uncertain",
            confidence_note="Eligibility analysis is unavailable right now. " + CONFIDENCE_NOTE,
            findings=[],
            alternatives=_alternatives_as_models(guarantor_alts),
        )


def _validate_quotes(report: EligibilityReport, conditions_text: str) -> EligibilityReport:
    """NON-NEGOTIABLE per BUILD_SPEC.md 8.5: quoted_line must be a verbatim
    substring of conditions_text. Drop any finding that fails this check
    rather than let an ungrounded claim through."""
    valid_findings: list[EligibilityFinding] = []
    for finding in report.findings:
        if finding.quoted_line and finding.quoted_line in conditions_text:
            valid_findings.append(finding)
        else:
            logger.warning(
                "dropping eligibility finding with unverifiable quote: %r", finding.quoted_line
            )
    return report.model_copy(update={"findings": valid_findings})


def _alternatives_as_models(guarantor_alts: list[dict]):
    from schemas import Alternative

    return [Alternative(**a) for a in guarantor_alts]
