"use client";

import { useLanguage } from "@/lib/i18n";
import type { CostBreakdown, EligibilityReport, Listing, StrategyAdvice, TrustReport } from "@/lib/types";
import { CheckCircleIcon, ExternalLinkIcon, ShieldIcon, TrainIcon } from "./Icons";

export interface PartialCard {
  listing: Listing;
  match_reason: string;
  cost?: CostBreakdown;
  trust?: TrustReport;
  eligibility?: EligibilityReport;
  strategy?: StrategyAdvice;
  pros?: string[];
  cons?: string[];
}

const SOURCE_KEY: Record<Listing["source"], "sourceHomes" | "sourceSuumo" | "sourceUr" | "sourceManual"> = {
  homes: "sourceHomes",
  suumo: "sourceSuumo",
  ur: "sourceUr",
  manual: "sourceManual",
};

const SOURCE_PILL: Record<Listing["source"], string> = {
  homes: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
  suumo: "bg-orange-500/10 text-orange-700 dark:text-orange-400",
  ur: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  manual: "bg-ink/10 text-ink/60 dark:text-ink-dark/60",
};

const RISK_STYLE: Record<TrustReport["risk"], string> = {
  clear: "bg-green-500/10 text-green-700 dark:text-green-400",
  caution: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
  high_risk: "bg-red-500/10 text-signal font-semibold",
};
const RISK_KEY: Record<TrustReport["risk"], "riskClear" | "riskCaution" | "riskHigh"> = {
  clear: "riskClear",
  caution: "riskCaution",
  high_risk: "riskHigh",
};

const OUTLOOK_STYLE: Record<EligibilityReport["outlook"], string> = {
  likely: "bg-green-500/10 text-green-700 dark:text-green-400",
  uncertain: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
  unlikely: "bg-red-500/10 text-signal font-semibold",
};
const OUTLOOK_KEY: Record<EligibilityReport["outlook"], "outlookLikely" | "outlookUncertain" | "outlookUnlikely"> = {
  likely: "outlookLikely",
  uncertain: "outlookUncertain",
  unlikely: "outlookUnlikely",
};

function yen(n: number) {
  return `¥${n.toLocaleString("en-US")}`;
}

export default function ShortlistCard({
  card,
  onOpenDetail,
}: {
  card: PartialCard;
  onOpenDetail: () => void;
}) {
  const { t, lang } = useLanguage();
  const { listing, cost, trust, eligibility, pros = [], cons = [] } = card;

  return (
    <div className="card p-4 flex flex-col gap-3 h-full">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-medium leading-snug line-clamp-1">{listing.title}</h3>
          <p className="text-xs text-ink/60 dark:text-ink-dark/60 line-clamp-2 flex flex-wrap items-center gap-x-1">
            <span>{listing.ward ?? listing.address}</span>
            {listing.nearest_station && (
              <span className="flex items-center gap-0.5">
                <TrainIcon size={11} className="shrink-0" />
                {listing.nearest_station}
              </span>
            )}
            {listing.walk_minutes != null && (
              <span>
                {lang === "ja" ? `(徒歩${listing.walk_minutes}分)` : `(${listing.walk_minutes} min walk)`}
              </span>
            )}
          </p>
        </div>
        <span className={`pill whitespace-nowrap shrink-0 ${SOURCE_PILL[listing.source]}`}>
          {t(SOURCE_KEY[listing.source])}
        </span>
      </div>

      <div className="flex items-baseline gap-3 border-y border-rule dark:border-rule-dark py-2.5">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-ink/50 dark:text-ink-dark/50">
            {t("advertised")}
          </div>
          <div className="tabular-figures line-through text-ink/40 dark:text-ink-dark/40">
            {yen(listing.rent_jpy)}
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-ink/50 dark:text-ink-dark/50">
            {t("actually")}
          </div>
          {cost ? (
            <div className="tabular-figures text-lg font-semibold text-signal">
              {yen(cost.effective_monthly_jpy)}
              <span className="text-xs font-normal text-ink/60 dark:text-ink-dark/60 ml-1">
                /mo (+{cost.markup_percent.toFixed(0)}%)
              </span>
            </div>
          ) : (
            <div className="h-6 w-24 bg-gradient-to-r from-rule/40 to-rule/10 dark:from-rule-dark/40 dark:to-rule-dark/10 rounded animate-pulse" />
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 text-xs items-center">
        <span className="pill bg-ink/5 dark:bg-white/5">{listing.layout ?? "—"}</span>
        <span className="pill bg-ink/5 dark:bg-white/5">
          {listing.area_sqm ? `${listing.area_sqm}m²` : "—"}
        </span>
        {trust ? (
          <span className={`pill ${RISK_STYLE[trust.risk]}`} title={t("trustLabel")}>
            <ShieldIcon size={11} /> {t(RISK_KEY[trust.risk])}
          </span>
        ) : (
          <span className="pill bg-ink/5 dark:bg-white/5 text-ink/30 dark:text-ink-dark/30">
            <ShieldIcon size={11} /> {t("checkingTrust")}
          </span>
        )}
        {eligibility ? (
          <span className={`pill ${OUTLOOK_STYLE[eligibility.outlook]}`} title={t("eligibilityLabel")}>
            <CheckCircleIcon size={11} /> {t(OUTLOOK_KEY[eligibility.outlook])}
          </span>
        ) : (
          <span className="pill bg-ink/5 dark:bg-white/5 text-ink/30 dark:text-ink-dark/30">
            <CheckCircleIcon size={11} /> {t("checkingEligibility")}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs min-h-[3.5rem]">
        <ul className="space-y-1">
          {pros.slice(0, 3).map((p, i) => (
            <li key={i} className="text-green-700 dark:text-green-400 line-clamp-2">
              + {p}
            </li>
          ))}
        </ul>
        <ul className="space-y-1">
          {cons.slice(0, 3).map((c, i) => (
            <li key={i} className="text-signal line-clamp-2">
              − {c}
            </li>
          ))}
        </ul>
      </div>

      <p className="text-xs italic text-ink/50 dark:text-ink-dark/50 line-clamp-1">{card.match_reason}</p>

      <div className="flex items-center justify-between pt-1 mt-auto">
        {listing.source_url ? (
          <a
            href={listing.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs underline text-ink/70 dark:text-ink-dark/70 hover:text-signal"
          >
            {t("viewOriginal")} <ExternalLinkIcon size={11} />
          </a>
        ) : (
          <span />
        )}
        <button
          onClick={onOpenDetail}
          className="text-xs font-medium border border-rule dark:border-rule-dark rounded-lg px-3 py-1.5 hover:bg-ink/5 dark:hover:bg-white/5 transition-colors"
        >
          {t("details")}
        </button>
      </div>
    </div>
  );
}
