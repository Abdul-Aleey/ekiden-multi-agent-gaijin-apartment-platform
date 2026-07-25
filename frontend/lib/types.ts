// Mirrors backend/schemas.py exactly — keep these two in sync.

export type VisaType =
  | "engineer_specialist"
  | "student"
  | "permanent"
  | "spouse_of_japanese"
  | "dependent"
  | "specified_skilled"
  | "business_manager"
  | "working_holiday"
  | "other";

export interface ApplicantProfile {
  nationality: string;
  visa_type: VisaType;
  visa_expiry?: string | null;
  employment_status:
    | "seishain"
    | "keiyaku"
    | "haken"
    | "self_employed"
    | "student"
    | "job_offer"
    | "unemployed";
  annual_income_jpy?: number | null;
  japanese_level: "none" | "n5" | "n4" | "n3" | "n2" | "n1" | "native";
  guarantor_available: boolean;
  emergency_contact_in_japan: boolean;
  household_size: number;
}

export interface SearchPreferences {
  area_or_ward?: string | null;
  max_budget_jpy?: number | null;
  layouts: string[];
  min_area_sqm?: number | null;
  max_walk_minutes?: number | null;
  must_haves: string[];
  missing_critical_fields: string[];
}

export interface Listing {
  id: string;
  source: "homes" | "suumo" | "ur" | "manual";
  source_url?: string | null;
  title: string;
  address?: string | null;
  ward?: string | null;
  nearest_station?: string | null;
  line?: string | null;
  walk_minutes?: number | null;
  layout?: string | null;
  area_sqm?: number | null;
  building_year?: number | null;
  floor?: string | null;
  rent_jpy: number;
  kanrihi_jpy: number;
  shikikin_months?: number | null;
  reikin_months?: number | null;
  conditions_text?: string | null;
  raw_flags: string[];
  posted_date?: string | null;
}

export interface CostBreakdown {
  listing_id: string;
  advertised_monthly_jpy: number;
  upfront_total_jpy: number;
  effective_monthly_jpy: number;
  markup_percent: number;
  assumptions: string[];
}

export interface TrustSignal {
  code: "price_outlier" | "stale_posting" | "vague_address" | "missing_fees" | "no_property_id";
  severity: "high" | "medium" | "low";
  explanation_en: string;
  evidence: string;
}

export interface TrustReport {
  listing_id: string;
  risk: "clear" | "caution" | "high_risk";
  signals: TrustSignal[];
}

export interface EligibilityFinding {
  requirement_ja: string;
  requirement_en: string;
  verdict: "pass" | "concern" | "blocker";
  quoted_line: string;
  quoted_line_gloss?: string | null;
  advice_en: string;
}

export interface Alternative {
  kind: "ur" | "guarantor_company";
  name: string;
  why_en: string;
  url?: string | null;
}

export interface EligibilityReport {
  listing_id: string;
  outlook: "likely" | "uncertain" | "unlikely";
  confidence_note: string;
  findings: EligibilityFinding[];
  alternatives: Alternative[];
}

export interface StrategyAdvice {
  listing_id: string;
  plan: string;
}

export interface ListingCard {
  listing: Listing;
  cost: CostBreakdown;
  trust: TrustReport;
  eligibility: EligibilityReport;
  strategy: StrategyAdvice;
  pros: string[];
  cons: string[];
  match_reason: string;
}

export interface InquiryEmail {
  listing_id: string;
  subject_ja: string;
  body_ja: string;
  body_en_gloss: string;
}

export type SourceStatus = "live_both" | "live_homes_only" | "live_suumo_only" | "fallback";
