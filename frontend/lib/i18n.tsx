"use client";

import { createContext, useContext, useState } from "react";

export type Lang = "en" | "ja";

const DICT = {
  tagline: { en: "Know before you sign.", ja: "契約する前に、知る。" },
  subhead: {
    en: "Ekiden searches live listings anywhere in Japan, reveals the true cost beyond advertised rent, and reads your eligibility straight from what each listing actually says.",
    ja: "Ekidenは日本全国の物件をリアルタイムで検索し、広告家賃だけでなく実質費用を明らかにし、掲載内容から入居可否を直接読み取ります。",
  },
  profileTitle: { en: "Applicant profile", ja: "申込者情報" },
  profileEdit: { en: "Edit", ja: "編集" },
  profileHide: { en: "Hide", ja: "閉じる" },
  fieldNationality: { en: "Nationality", ja: "国籍" },
  fieldVisaType: { en: "Visa type", ja: "在留資格" },
  fieldEmployment: { en: "Employment", ja: "就業形態" },
  fieldIncome: { en: "Annual income (JPY)", ja: "年収" },
  fieldJapanese: { en: "Japanese level", ja: "日本語レベル" },
  fieldHousehold: { en: "Household size", ja: "入居人数" },
  fieldGuarantor: { en: "Guarantor available in Japan", ja: "連帯保証人あり" },
  fieldEmergencyContact: { en: "Emergency contact in Japan", ja: "緊急連絡先あり" },
  chatPlaceholder: {
    en: "Tell Ekiden what you're looking for—area, budget, layout, must-haves...",
    ja: "エリア・予算・間取りなどのご希望を教えてください...",
  },
  chatHint: { en: "Cmd/Ctrl + Enter to send", ja: "Cmd/Ctrl + Enter で送信" },
  btnSearching: { en: "Searching…", ja: "検索中…" },
  btnAnswer: { en: "Answer", ja: "回答する" },
  btnFind: { en: "Find apartments", ja: "検索する" },
  ekidenAsks: { en: "Ekiden asks:", ja: "質問:" },
  stepPrefs: { en: "Reading your preferences", ja: "ご希望を確認中" },
  stepSearch: { en: "Searching listings", ja: "物件を検索中" },
  stepRank: { en: "Deduping & ranking matches", ja: "重複除去・ランキング中" },
  stepAnalyze: { en: "Computing true cost, trust & eligibility", ja: "実質費用・信頼性・入居条件を分析中" },
  candidatesShortlisted: { en: "candidates shortlisted", ja: "件の候補" },
  listingsAnalyzed: { en: "listings analyzed", ja: "件を分析済み" },
  emptyShortlist: { en: "Your shortlist will appear here once you search.", ja: "検索結果はここに表示されます" },
  advertised: { en: "Advertised", ja: "広告家賃" },
  actually: { en: "Actually", ja: "実質" },
  checkingTrust: { en: "checking trust…", ja: "信頼性を確認中…" },
  checkingEligibility: { en: "checking eligibility…", ja: "入居条件を確認中…" },
  viewOriginal: { en: "View original listing", ja: "元の掲載を見る" },
  details: { en: "Details", ja: "詳細" },
  close: { en: "Close", ja: "閉じる" },
  trueCost: { en: "True cost", ja: "実質費用" },
  upfrontTotal: { en: "Upfront total", ja: "初期費用合計" },
  effectiveMonthly: { en: "Effective monthly", ja: "実質月額" },
  eligibility: { en: "Eligibility", ja: "入居条件" },
  askAbout: { en: "Ask about this listing", ja: "この物件について質問する" },
  askPlaceholder: { en: "e.g. Is this pet friendly?", ja: "例: ペット可能ですか？" },
  ask: { en: "Ask", ja: "質問する" },
  inquiryEmail: { en: "Inquiry email", ja: "問い合わせメール" },
  draftEmail: { en: "Draft inquiry email", ja: "問い合わせメールを作成" },
  drafting: { en: "Drafting…", ja: "作成中…" },
  copy: { en: "Copy", ja: "コピー" },
  copied: { en: "Copied!", ja: "コピーしました！" },
  englishGloss: { en: "English gloss", ja: "英語訳" },
  sourceLiveBoth: { en: "Live results", ja: "ライブ検索結果" },
  sourceLiveHomes: { en: "Live results (partial)", ja: "ライブ検索結果（一部）" },
  sourceLiveSuumo: { en: "Live results (partial)", ja: "ライブ検索結果（一部）" },
  sourceFallback: {
    en: "Live sites unreachable — showing our real Tokyo fallback corpus (UR + hand-collected)",
    ja: "ライブサイトに接続できないため、実データのフォールバック（UR＋手動収集）を表示中",
  },
  sourceNoData: {
    en: "No live results and no fallback data for this area yet",
    ja: "このエリアはライブ結果もフォールバックデータもまだありません",
  },
  trustLabel: { en: "Bait-listing trust check", ja: "おとり物件チェック" },
  eligibilityLabel: { en: "Your eligibility", ja: "入居可否" },
  riskClear: { en: "Clear", ja: "良好" },
  riskCaution: { en: "Caution", ja: "注意" },
  riskHigh: { en: "High risk", ja: "要注意" },
  outlookLikely: { en: "Likely eligible", ja: "可能性高" },
  outlookUncertain: { en: "Uncertain", ja: "不確実" },
  outlookUnlikely: { en: "Unlikely", ja: "難しい" },
  sourceHomes: { en: "LIFULL HOME'S", ja: "LIFULL HOME'S" },
  sourceSuumo: { en: "SUUMO", ja: "SUUMO" },
  sourceUr: { en: "UR Housing", ja: "UR賃貸" },
  sourceManual: { en: "Manual", ja: "手動登録" },
  matchedFilters: { en: "Matched on ward/budget/layout filters", ja: "予算・間取り・エリアの条件に一致" },
  fieldMustHaves: { en: "Must-haves", ja: "必須条件" },
  areaResolvedModel: { en: "location understood by AI", ja: "AIが場所を認識" },
  areaResolvedFallback: { en: "location matched by dictionary lookup", ja: "辞書照合で場所を特定" },
  areaNotResolved: { en: "couldn't identify a location", ja: "場所を特定できませんでした" },
  statPrefectures: { en: "prefectures searched live", ja: "都道府県でライブ検索" },
  statCities: { en: "cities, towns & villages covered", ja: "市区町村をカバー" },
  statReal: { en: "real data, zero synthetic", ja: "実データ、合成データ0" },
} as const;

export type DictKey = keyof typeof DICT;

interface LanguageContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: DictKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");
  const t = (key: DictKey) => DICT[key][lang];
  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>{children}</LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
