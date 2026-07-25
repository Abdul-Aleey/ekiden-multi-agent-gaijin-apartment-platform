"use client";

import { useMemo, useRef, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import CostRevealDemo from "@/components/CostRevealDemo";
import JapanNetworkMap from "@/components/JapanNetworkMap";
import ListingDetail from "@/components/ListingDetail";
import NavBar from "@/components/NavBar";
import ProfileForm, { DEMO_PROFILE } from "@/components/ProfileForm";
import SearchProgress, { ProgressStep } from "@/components/SearchProgress";
import ShortlistCard, { PartialCard } from "@/components/ShortlistCard";
import { streamChat } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { ApplicantProfile, SearchPreferences, SourceStatus } from "@/lib/types";

const SOURCE_STATUS_LABEL: Record<SourceStatus | "no_data", { en: string; ja: string }> = {
  live_both: { en: "Live from HOME'S + SUUMO", ja: "HOME'SとSUUMOのライブ結果" },
  live_homes_only: { en: "Live from HOME'S only (SUUMO unavailable)", ja: "HOME'Sのみ（SUUMO利用不可）" },
  live_suumo_only: { en: "Live from SUUMO only (HOME'S unavailable)", ja: "SUUMOのみ（HOME'S利用不可）" },
  fallback: {
    en: "Live sites unreachable — showing our real Tokyo fallback corpus (UR + hand-collected)",
    ja: "ライブサイトに接続できないため、実データのフォールバック（UR＋手動収集）を表示中",
  },
  no_data: {
    en: "No live results and no fallback data for this area yet",
    ja: "このエリアはライブ結果もフォールバックデータもまだありません",
  },
};

const STAGE_ORDER = ["preferences", "search", "rank", "analyze", "done"] as const;
type Stage = (typeof STAGE_ORDER)[number];

export default function Page() {
  const { lang, t } = useLanguage();
  const [profile, setProfile] = useState<ApplicantProfile>(DEMO_PROFILE);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<Stage>("preferences");
  const [clarifyQuestion, setClarifyQuestion] = useState<string | null>(null);
  const [priorPrefs, setPriorPrefs] = useState<SearchPreferences | null>(null);
  const [sourceStatus, setSourceStatus] = useState<SourceStatus | "no_data" | null>(null);
  const [areaResolution, setAreaResolution] = useState<"model" | "fallback" | "none" | null>(null);
  const [searchProgressText, setSearchProgressText] = useState<string | null>(null);
  const [order, setOrder] = useState<string[]>([]);
  const [cards, setCards] = useState<Record<string, PartialCard>>({});
  const [analyzedCount, setAnalyzedCount] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stageStatus = (key: Stage): ProgressStep["status"] => {
    const cur = STAGE_ORDER.indexOf(stage);
    const at = STAGE_ORDER.indexOf(key);
    if (at < cur) return "done";
    if (at === cur) return "active";
    return "pending";
  };

  const steps: ProgressStep[] = useMemo(
    () => [
      { label: t("stepPrefs"), status: stageStatus("preferences") },
      {
        label: t("stepSearch"),
        status: stageStatus("search"),
        detail: sourceStatus
          ? [
              SOURCE_STATUS_LABEL[sourceStatus][lang],
              areaResolution === "model"
                ? t("areaResolvedModel")
                : areaResolution === "fallback"
                ? t("areaResolvedFallback")
                : areaResolution === "none"
                ? t("areaNotResolved")
                : null,
            ]
              .filter(Boolean)
              .join(" · ")
          : searchProgressText ?? undefined,
      },
      {
        label: t("stepRank"),
        status: stageStatus("rank"),
        detail: order.length ? `${order.length} ${t("candidatesShortlisted")}` : undefined,
      },
      {
        label: t("stepAnalyze"),
        status: stageStatus("analyze"),
        detail: order.length ? `${analyzedCount}/${order.length} ${t("listingsAnalyzed")}` : undefined,
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [stage, sourceStatus, areaResolution, searchProgressText, order.length, analyzedCount, lang]
  );

  const handleSend = async (message: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setErrorMsg(null);
    setClarifyQuestion(null);
    setOrder([]);
    setCards({});
    setSourceStatus(null);
    setAreaResolution(null);
    setSearchProgressText(null);
    setAnalyzedCount(0);
    setStage("preferences");

    try {
      for await (const evt of streamChat(message, profile, priorPrefs, lang, controller.signal)) {
        switch (evt.event) {
          case "stage":
            if (evt.data.stage === "preferences") setStage("preferences");
            if (evt.data.stage === "search") setStage("search");
            break;

          case "clarify":
            setClarifyQuestion(evt.data.question);
            setPriorPrefs(evt.data.prefs);
            setLoading(false);
            break;

          case "search_progress": {
            const { status, count, cities } = evt.data;
            if (status === "expanding") {
              setSearchProgressText(
                lang === "ja" ? `${cities}件の都市を検索中...` : `Expanding to ${cities} cities...`
              );
            } else if (status === "fetching" && typeof count === "number") {
              setSearchProgressText(
                lang === "ja" ? `${count}件を発見...` : `${count} listings found so far...`
              );
            } else if (status === "fetching") {
              setSearchProgressText(lang === "ja" ? "検索中..." : "Searching listings...");
            }
            break;
          }

          case "shortlist": {
            setSourceStatus(evt.data.source_status);
            setAreaResolution(evt.data.area_resolution ?? null);
            setStage("rank");
            setTimeout(() => setStage("analyze"), 300);
            const listings = evt.data.listings as (PartialCard["listing"] & { match_reason: string })[];
            setOrder(listings.map((l) => l.id));
            const next: Record<string, PartialCard> = {};
            for (const l of listings) {
              const { match_reason, ...listing } = l;
              next[l.id] = { listing, match_reason };
            }
            setCards(next);
            break;
          }

          case "cost":
            setCards((prev) => {
              const { listing_id, ...cost } = evt.data;
              const existing = prev[listing_id];
              if (!existing) return prev;
              return { ...prev, [listing_id]: { ...existing, cost } };
            });
            break;

          case "trust":
            setCards((prev) => {
              const { listing_id, ...trust } = evt.data;
              const existing = prev[listing_id];
              if (!existing) return prev;
              return { ...prev, [listing_id]: { ...existing, trust } };
            });
            break;

          case "eligibility":
            setCards((prev) => {
              const { listing_id, ...eligibility } = evt.data;
              const existing = prev[listing_id];
              if (!existing) return prev;
              return { ...prev, [listing_id]: { ...existing, eligibility } };
            });
            break;

          case "strategy":
            setCards((prev) => {
              const { listing_id, ...strategy } = evt.data;
              const existing = prev[listing_id];
              if (!existing) return prev;
              return { ...prev, [listing_id]: { ...existing, strategy } };
            });
            break;

          case "card":
            setAnalyzedCount((n) => n + 1);
            setCards((prev) => {
              const existing = prev[evt.data.listing.id];
              return {
                ...prev,
                [evt.data.listing.id]: {
                  listing: evt.data.listing,
                  match_reason: evt.data.match_reason ?? existing?.match_reason ?? "",
                  cost: evt.data.cost,
                  trust: evt.data.trust,
                  eligibility: evt.data.eligibility,
                  strategy: evt.data.strategy,
                  pros: evt.data.pros,
                  cons: evt.data.cons,
                },
              };
            });
            break;

          case "error":
            setErrorMsg(`Something went wrong analyzing one listing (${evt.data.stage}). The rest still loaded.`);
            break;

          case "done":
            setStage("done");
            setLoading(false);
            break;
        }
      }
    } catch (e) {
      if (!controller.signal.aborted) {
        setErrorMsg("Couldn't reach Ekiden's backend. Is it running?");
      }
    } finally {
      setLoading(false);
    }
  };

  const selectedCard = selectedId ? cards[selectedId] : null;

  return (
    <main className="min-h-screen">
      <NavBar />

      <div className="hero-glow grid-texture border-b border-rule dark:border-rule-dark overflow-hidden relative">
        <div className="absolute inset-y-0 left-[6%] md:left-[10%] w-full md:w-[58%] p-10 md:p-16 pointer-events-none">
          <JapanNetworkMap />
        </div>

        <div className="max-w-6xl mx-auto px-4 py-14 md:py-20 grid grid-cols-1 md:grid-cols-[1.1fr_0.9fr] gap-10 items-center relative z-10">
          <div className="animate-fade-in-up">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-[1.1] mb-4">
              <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-signal bg-clip-text text-transparent">
                {t("tagline")}
              </span>
            </h1>
            <p className="text-base text-ink/70 dark:text-ink-dark/70 max-w-xl">{t("subhead")}</p>
          </div>

          <div className="flex justify-center md:justify-end animate-fade-in-up" style={{ animationDelay: "120ms" }}>
            <CostRevealDemo />
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-4 pb-12 md:pb-16 grid grid-cols-3 gap-4 sm:gap-6 relative z-10 animate-fade-in-up" style={{ animationDelay: "200ms" }}>
          {[
            { value: "47", key: "statPrefectures" as const },
            { value: "1,718", key: "statCities" as const },
            { value: "100%", key: "statReal" as const },
          ].map((s) => (
            <div key={s.key}>
              <div className="text-2xl font-bold tabular-figures bg-gradient-to-r from-indigo-600 to-signal bg-clip-text text-transparent">
                {s.value}
              </div>
              <div className="text-[11px] text-ink/50 dark:text-ink-dark/50 leading-tight">
                {t(s.key)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="dot-texture">
        <div className="max-w-6xl mx-auto px-4 py-10 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-8">
          <div className="lg:sticky lg:top-24 lg:self-start flex flex-col gap-4">
            <ProfileForm profile={profile} onChange={setProfile} />
            <ChatPanel onSend={handleSend} loading={loading} clarifyQuestion={clarifyQuestion} />
            {errorMsg && <p className="text-xs text-signal">{errorMsg}</p>}
          </div>

          <div className="flex flex-col gap-4">
            {loading && <SearchProgress steps={steps} />}

            {!loading && order.length === 0 && (
              <div className="text-sm text-ink/50 dark:text-ink-dark/50 border border-dashed border-rule dark:border-rule-dark rounded-2xl p-10 text-center">
                {t("emptyShortlist")}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {order.map((id, i) => {
                const card = cards[id];
                if (!card) return null;
                return (
                  <div key={id} className="animate-fade-in-up h-full" style={{ animationDelay: `${i * 60}ms` }}>
                    <ShortlistCard card={card} onOpenDetail={() => setSelectedId(id)} />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {selectedCard && (
        <ListingDetail card={selectedCard} profile={profile} onClose={() => setSelectedId(null)} />
      )}
    </main>
  );
}
