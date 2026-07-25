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
  const { lang } = useLanguage();
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
      setAnswer("Sorry, that request failed. Please try again.");
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
                View original listing / 元の掲載を見る ↗
              </a>
            )}
          </div>
          <button onClick={onClose} className="text-sm px-2 py-1 border border-rule dark:border-rule-dark rounded">
            Close / 閉じる
          </button>
        </div>

        {cost && (
          <section className="card p-4">
            <h3 className="text-sm font-medium mb-2">True cost / 実質費用</h3>
            <div className="text-sm space-y-1 tabular-figures">
              <div>Advertised / 広告家賃: ¥{cost.advertised_monthly_jpy.toLocaleString()}</div>
              <div>Upfront total / 初期費用合計: ¥{cost.upfront_total_jpy.toLocaleString()}</div>
              <div className="text-signal font-semibold">
                Effective monthly / 実質月額: ¥{cost.effective_monthly_jpy.toLocaleString()} (+
                {cost.markup_percent.toFixed(0)}%)
              </div>
            </div>
            {cost.assumptions.length > 0 && (
              <p className="mt-2 text-[11px] text-ink/50 dark:text-ink-dark/50">
                Based only on fees this listing actually states — nothing above is estimated. Below:
                what wasn&apos;t stated, so the real total could be higher.
                <span className="block">
                  実際に記載されている費用のみで計算しています（推定なし）。以下は記載がなく、実際の総額はさらに高くなる可能性があります。
                </span>
              </p>
            )}
            <ul className="mt-2 text-xs text-ink/60 dark:text-ink-dark/60 list-disc list-inside space-y-0.5">
              {cost.assumptions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </section>
        )}

        {eligibility && (
          <section className="card p-4">
            <h3 className="text-sm font-medium mb-2">Eligibility / 入居条件</h3>
            <p className="text-xs italic text-ink/60 dark:text-ink-dark/60 mb-2">
              {eligibility.confidence_note}
            </p>
            <div className="space-y-3">
              {eligibility.findings.length === 0 && (
                <p className="text-xs text-ink/50 dark:text-ink-dark/50">
                  No specific conditions could be grounded in the listing's text.
                </p>
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
            <h3 className="text-sm font-medium mb-2">🎯 Strategy advisor / 交渉戦略</h3>
            <p className="text-[11px] text-ink/50 dark:text-ink-dark/50 mb-2">
              Not guaranteed — a real starting point for a conversation, not an entitlement.
              <span className="block">交渉の結果を保証するものではありません。あくまで会話の出発点としてご活用ください。</span>
            </p>
            <p className="text-xs whitespace-pre-wrap text-ink/80 dark:text-ink-dark/80">{strategy.plan}</p>
          </section>
        )}

        <section className="card p-4">
          <h3 className="text-sm font-medium mb-2">Ask about this listing</h3>
          <div className="flex gap-2">
            <input
              className="input flex-1"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Is this pet friendly?"
              onKeyDown={(e) => e.key === "Enter" && ask()}
            />
            <button className="btn-primary" onClick={ask} disabled={askLoading}>
              {askLoading ? "…" : "Ask"}
            </button>
          </div>
          {answer && <p className="text-xs mt-2 text-ink/70 dark:text-ink-dark/70">{answer}</p>}
        </section>

        <section className="card p-4">
          <h3 className="text-sm font-medium mb-2">Inquiry email / 問い合わせメール</h3>
          {!email ? (
            <button className="btn-primary" onClick={draftEmail} disabled={emailLoading}>
              {emailLoading ? "Drafting…" : "Draft inquiry email"}
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
                {copied ? "Copied!" : "Copy"}
              </button>
              <details className="mt-2">
                <summary className="cursor-pointer text-ink/60 dark:text-ink-dark/60">
                  English gloss
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
