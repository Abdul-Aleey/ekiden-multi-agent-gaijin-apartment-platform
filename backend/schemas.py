from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

VisaType = Literal[
    "engineer_specialist",
    "student",
    "permanent",
    "spouse_of_japanese",
    "dependent",
    "specified_skilled",
    "business_manager",
    "working_holiday",
    "other",
]


class ApplicantProfile(BaseModel):
    nationality: str
    visa_type: VisaType
    visa_expiry: Optional[date] = None
    employment_status: Literal[
        "seishain", "keiyaku", "haken", "self_employed", "student", "job_offer", "unemployed"
    ]
    annual_income_jpy: Optional[int] = None
    japanese_level: Literal["none", "n5", "n4", "n3", "n2", "n1", "native"]
    guarantor_available: bool
    emergency_contact_in_japan: bool
    household_size: int = 1


class SearchPreferences(BaseModel):
    area_or_ward: Optional[str] = None
    max_budget_jpy: Optional[int] = None
    layouts: list[str] = []  # e.g. ["1K", "1DK"] — a user asking "1K or 1DK" wants either, not just one
    min_area_sqm: Optional[float] = None
    max_walk_minutes: Optional[int] = None
    must_haves: list[str] = []
    missing_critical_fields: list[str] = []


class Listing(BaseModel):
    id: str
    source: Literal["homes", "suumo", "ur", "manual"]
    source_url: Optional[str] = None
    title: str
    address: Optional[str] = None
    ward: Optional[str] = None
    nearest_station: Optional[str] = None
    line: Optional[str] = None
    walk_minutes: Optional[int] = None
    layout: Optional[str] = None
    area_sqm: Optional[float] = None
    building_year: Optional[int] = None
    floor: Optional[str] = None
    rent_jpy: int
    kanrihi_jpy: int = 0
    shikikin_months: Optional[float] = None
    reikin_months: Optional[float] = None
    conditions_text: Optional[str] = None
    raw_flags: list[str] = []
    posted_date: Optional[str] = None


class CostLineItem(BaseModel):
    label_en: str
    amount_jpy: int


class CostBreakdown(BaseModel):
    listing_id: str
    advertised_monthly_jpy: int
    # Each *_items list is guaranteed (by construction in services/daytona.py) to
    # sum exactly to its corresponding total — the three categories are mutually
    # exclusive, not overlapping views of the same money:
    #   upfront_items -> upfront_total_jpy: paid once, at move-in.
    #   effective_monthly_items -> effective_monthly_jpy: ongoing monthly cost,
    #     amortizing the upfront one-time fees over a standard 2-year lease.
    #   renewal_items: periodic costs after move-in (guarantor renewal, lease
    #     renewal fee) — deliberately NOT folded into either total above, shown
    #     separately with their own real amount and real timing.
    upfront_total_jpy: int
    upfront_items: list[CostLineItem] = []
    effective_monthly_jpy: int
    effective_monthly_items: list[CostLineItem] = []
    renewal_items: list[CostLineItem] = []
    markup_percent: float
    assumptions: list[str] = []


class TrustSignal(BaseModel):
    code: Literal["price_outlier", "stale_posting", "vague_address", "missing_fees", "no_property_id"]
    severity: Literal["high", "medium", "low"]
    explanation_en: str
    evidence: str


class TrustReport(BaseModel):
    listing_id: str
    risk: Literal["clear", "caution", "high_risk"]
    signals: list[TrustSignal] = []


class EligibilityFinding(BaseModel):
    requirement_ja: str
    requirement_en: str
    verdict: Literal["pass", "concern", "blocker"]
    quoted_line: str
    quoted_line_gloss: Optional[str] = None
    advice_en: str


class Alternative(BaseModel):
    kind: Literal["ur", "guarantor_company"]
    name: str
    why_en: str
    url: Optional[str] = None


class EligibilityReport(BaseModel):
    listing_id: str
    outlook: Literal["likely", "uncertain", "unlikely"]
    confidence_note: str
    findings: list[EligibilityFinding] = []
    alternatives: list[Alternative] = []


class StrategyAdvice(BaseModel):
    listing_id: str
    plan: str = ""


class ListingCard(BaseModel):
    listing: Listing
    cost: CostBreakdown
    trust: TrustReport
    eligibility: EligibilityReport
    strategy: StrategyAdvice
    pros: list[str] = []
    cons: list[str] = []
    match_reason: str = ""


class InquiryEmail(BaseModel):
    listing_id: str
    subject_ja: str
    body_ja: str
    body_en_gloss: str


class ChatTurnRequest(BaseModel):
    message: str
    profile: ApplicantProfile
    prior_prefs: Optional[SearchPreferences] = None
    lang: Literal["en", "ja"] = "en"


class FollowupRequest(BaseModel):
    listing_id: str
    question: str
    lang: Literal["en", "ja"] = "en"


class InquiryRequest(BaseModel):
    listing_id: str
    profile: ApplicantProfile
