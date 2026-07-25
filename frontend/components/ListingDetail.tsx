"use client";

import { useState } from "react";
import { askFollowup, generateInquiry } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { ApplicantProfile, InquiryEmail } from "@/lib/types";
import type { PartialCard } from "./ShortlistCard";

const VERDICT_STYLE: Record<string, string> = {
  pass: "text-green-700 dark:text-green-400",
  concern: "text-amber-700 dark:text-amber-400",
  blocker: "text-signal font-semibold",
};

export default function ListingDetail({
  card,
  profile,
  onClose,
}: {
  card: PartialCard;
  profile: ApplicantProfile;
  onClose: () => void;
}) {
  const { listing, cost, eligibility, strategy } = card;
  const { lang, t } = useLanguage();
  const FREQ_LABEL: Record<string, string> = {
    monthly: t("costFreqMonthly"),
    "one-time": t("costFreqOneTime"),
    "per year": t("costFreqPerYear"),
    "at each renewal": t("costFreqRenewal"),
  };
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [askLoading, setAskLoading] = useState(false);
  const [email, setEmail] = useState<InquiryEmail | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const ask = async () => {
    if (!question.trim()) return;
    setAskLoading(true);
    try {
      const a = await askFollowup(listing.id, question.trim(), lang);
      setAnswer(a);
    } catch (e) {
      setAnswer(t("askFailed"));
    } finally {
      setAskLoading(false);
    }
  };

  const draftEmail = async () => {
    setEmailLoading(true);
    try {
      const e = await generateInquiry(listing.id, profile);
      setEmail(e);
    } catch {
      setEmail(null);
    } finally {
      setEmailLoading(false);
    }
  };

  const copyEmail = () => {
    if (!email) return;
    navigator.clipboard.writeText(email.body_ja);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex justify-end z-50" onClick={onClose}>
      <div
        className="bg-paper dark:bg-paper-dark w-full max-w-lg h-full overflow-y-auto p-6 flex flex-col gap-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold">{listing.title}</h2>
            <p className="text-sm text-ink/60 dark:text-ink-dark/60">{listing.address}</p>
            {listing.source_url && (
              <a
                href={listing.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs underline text-ink/70 dark:text-ink-dark/70 hover:text-signal"
              >
                {t("viewOriginalListing")} ↗
              </a>
            )}
          </div>
          <button onClick={onClose} className="text-sm px-2 py-1 border border-rule dark:border-rule-dark rounded">
            {t("close")}
          </button>
        </div>

        {cost && (
          <section className="card p-4">
            <h3 className="text-sm font-medium mb-2">{t("trueCost")}</h3>
            <div className="text-sm space-y-1 tabular-figures">
              <div>{t("advertised")}: ¥{cost.advertised_monthly_jpy.toLocaleString()}</div>
              <div>{t("upfrontTotal")}: ¥{cost.upfront_total_jpy.toLocaleString()}</div>
              <div className="text-signal font-semibold">
                {t("effectiveMonthly")}: ¥{cost.effective_monthly_jpy.toLocaleString()} (+
                {cost.markup_percent.toFixed(0)}%)
              </div>
            </div>

            {cost.items.length > 0 && (
              <div className="mt-4">
                <h4 className="text-xs font-medium mb-1">{t("costBreakdownTitle")}</h4>
                <p className="text-[11px] text-ink/50 dark:text-ink-dark/50 mb-2">{t("costBreakdownIntro")}</p>
                <ul className="text-xs divide-y divide-rule dark:divide-rule-dark">
                  {cost.items.map((item, i) => (
                    <li key={i} className="flex items-center justify-between py-1.5 tabular-figures">
                      <span>{item.label_en}</span>
                      <span className="flex items-center gap-2">
                        <span className="text-ink/40 dark:text-ink-dark/40 text-[10px]">
                          {FREQ_LABEL[item.frequency_en] ?? item.frequency_en}
                        </span>
                        <span className="font-medium">¥{item.amount_jpy.toLocaleString()}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {cost.assumptions.length > 0 && (
              <div className="mt-4">
                <h4 className="text-xs font-medium mb-1">{t("costNotStatedTitle")}</h4>
                <p className="text-[11px] text-ink/50 dark:text-ink-dark/50 mb-2">{t("costDisclaimer")}</p>
                <ul className="text-xs text-ink/60 dark:text-ink-dark/60 list-disc list-inside space-y-0.5">
                  {cost.assumptions.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {eligibility && (
          <section className="card p-4">
            <h3 className="text-sm font-medium mb-2">{t("eligibility")}</h3>
            <p className="text-xs italic text-ink/60 dark:text-ink-dark/60 mb-2">
              {eligibility.confidence_note}
            </p>
            <div className="space-y-3">
              {eligibility.findings.length === 0 && (
                <p className="text-xs text-ink/50 dark:text-ink-dark/50">{t("noConditionsFound")}</p>
              )}
              {eligibility.findings.map((f, i) => (
                <div key={i} className="text-xs border-l-2 border-rule dark:border-rule-dark pl-2">
                  <div className={VERDICT_STYLE[f.verdict]}>
                    {f.requirement_en} — {f.verdict}
                  </div>
                  <div className="text-ink/50 dark:text-ink-dark/50">{f.advice_en}</div>
                  <div className="mt-1 font-mono bg-ink/5 dark:bg-white/5 rounded px-1.5 py-1">
                    「{f.quoted_line}」
                  </div>
                  {f.quoted_line_gloss && (
                    <div className="mt-1 text-ink/50 dark:text-ink-dark/50 italic">
                      &ldquo;{f.quoted_line_gloss}&rdquo;
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {strategy && strategy.plan && (
          <section className="card p-4">
            <h3 className="text-sm font-medium mb-2">🎯 {t("strategyAdvisorTitle")}</h3>
            <p className="text-[11px] text-ink/50 dark:text-ink-dark/50 mb-2">{t("strategyDisclaimer")}</p>
            <p className="text-xs whitespace-pre-wrap text-ink/80 dark:text-ink-dark/80">{strategy.plan}</p>
          </section>
        )}

        <section className="card p-4">
          <h3 className="text-sm font-medium mb-2">{t("askAbout")}</h3>
          <div className="flex gap-2">
            <input
              className="input flex-1"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={t("askPlaceholder")}
              onKeyDown={(e) => e.key === "Enter" && ask()}
            />
            <button className="btn-primary" onClick={ask} disabled={askLoading}>
              {askLoading ? "…" : t("ask")}
            </button>
          </div>
          {answer && <p className="text-xs mt-2 text-ink/70 dark:text-ink-dark/70">{answer}</p>}
        </section>

        <section className="card p-4">
          <h3 className="text-sm font-medium mb-2">{t("inquiryEmail")}</h3>
          {!email ? (
            <button className="btn-primary" onClick={draftEmail} disabled={emailLoading}>
              {emailLoading ? t("drafting") : t("draftEmail")}
            </button>
          ) : (
            <div className="space-y-2 text-xs">
              <div className="font-medium">{email.subject_ja}</div>
              <pre className="whitespace-pre-wrap font-sans bg-ink/5 dark:bg-white/5 rounded p-2">
                {email.body_ja}
              </pre>
              <button
                onClick={copyEmail}
                className="text-xs border border-rule dark:border-rule-dark rounded px-3 py-1"
              >
                {copied ? t("copied") : t("copy")}
              </button>
              <details className="mt-2">
                <summary className="cursor-pointer text-ink/60 dark:text-ink-dark/60">
                  {t("englishGloss")}
                </summary>
                <p className="mt-1 text-ink/70 dark:text-ink-dark/70">{email.body_en_gloss}</p>
              </details>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
