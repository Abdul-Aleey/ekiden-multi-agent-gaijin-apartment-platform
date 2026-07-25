"use client";

import { useEffect, useState } from "react";
import Logo from "@/components/Logo";
import { API_URL } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

type ProviderStatus = "ok" | "error" | "not_configured" | "configured_untested" | "checking";

const PROVIDERS: {
  label: string;
  key: "qwen" | "aiand_fast" | "aiand_quality" | "daytona" | "gemini";
}[] = [
  { label: "Qwen Cloud", key: "qwen" },
  { label: "ai& (fast)", key: "aiand_fast" },
  { label: "ai& (quality)", key: "aiand_quality" },
  { label: "Daytona", key: "daytona" },
  { label: "Vertex AI Gemini", key: "gemini" },
];

const DOT_STYLE: Record<ProviderStatus, string> = {
  ok: "bg-emerald-500",
  error: "bg-signal",
  not_configured: "bg-ink/25 dark:bg-white/25",
  configured_untested: "bg-amber-500",
  checking: "bg-ink/25 dark:bg-white/25 animate-pulse",
};

const TEXT_STYLE: Record<ProviderStatus, string> = {
  ok: "text-emerald-700 dark:text-emerald-400",
  error: "text-signal",
  not_configured: "text-ink/50 dark:text-ink-dark/50",
  configured_untested: "text-amber-700 dark:text-amber-400",
  checking: "text-ink/50 dark:text-ink-dark/50",
};

const TITLE: Record<ProviderStatus, string> = {
  ok: "Reachable — live call succeeded",
  error: "Configured but unreachable right now",
  not_configured: "Not configured yet",
  configured_untested: "Configured, not yet ping-tested",
  checking: "Checking…",
};

export default function NavBar() {
  const { lang, setLang } = useLanguage();
  const [status, setStatus] = useState<Record<string, ProviderStatus>>({
    qwen: "checking", aiand_fast: "checking", aiand_quality: "checking",
    daytona: "checking", gemini: "checking",
  });

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/api/status`)
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled) setStatus(data);
      })
      .catch(() => {
        if (!cancelled) {
          setStatus({
            qwen: "error", aiand_fast: "error", aiand_quality: "error",
            daytona: "error", gemini: "error",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="sticky top-0 z-40 glass-nav">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center gap-3">
        <Logo size={30} />
        <span className="font-bold tracking-tight">
          Ekiden <span className="font-normal text-ink/40 dark:text-ink-dark/40 text-sm">駅伝</span>
        </span>

        <span className="pill bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ml-2">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Live · Nationwide
        </span>

        <div className="ml-auto flex items-center gap-3">
          <div className="hidden sm:flex gap-1.5">
            {PROVIDERS.map((p) => {
              const s = status[p.key] ?? "checking";
              return (
                <span
                  key={p.key}
                  className={`pill bg-ink/5 dark:bg-white/5 ${TEXT_STYLE[s]}`}
                  title={`${p.label}: ${TITLE[s]}`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${DOT_STYLE[s]}`} />
                  {p.label}
                </span>
              );
            })}
          </div>
          <div className="flex rounded-full border border-rule dark:border-rule-dark overflow-hidden text-xs font-medium">
            <button
              onClick={() => setLang("en")}
              className={`px-3 py-1.5 transition-colors ${
                lang === "en"
                  ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white"
                  : "hover:bg-ink/5 dark:hover:bg-white/5"
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setLang("ja")}
              className={`px-3 py-1.5 transition-colors ${
                lang === "ja"
                  ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white"
                  : "hover:bg-ink/5 dark:hover:bg-white/5"
              }`}
            >
              日本語
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
