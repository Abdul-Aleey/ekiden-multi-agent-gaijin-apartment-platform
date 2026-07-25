"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/i18n";
import type { ApplicantProfile } from "@/lib/types";

export const DEMO_PROFILE: ApplicantProfile = {
  nationality: "United States",
  visa_type: "engineer_specialist",
  visa_expiry: "2028-03-31",
  employment_status: "seishain",
  annual_income_jpy: 5200000,
  japanese_level: "n3",
  guarantor_available: false,
  emergency_contact_in_japan: false,
  household_size: 1,
};

const VISA_OPTIONS: { value: ApplicantProfile["visa_type"]; en: string; ja: string }[] = [
  { value: "engineer_specialist", en: "Engineer / Specialist in Humanities", ja: "技術・人文知識・国際業務" },
  { value: "student", en: "Student", ja: "留学" },
  { value: "permanent", en: "Permanent Resident", ja: "永住者" },
  { value: "spouse_of_japanese", en: "Spouse of Japanese National", ja: "日本人の配偶者等" },
  { value: "dependent", en: "Dependent", ja: "家族滞在" },
  { value: "specified_skilled", en: "Specified Skilled Worker", ja: "特定技能" },
  { value: "business_manager", en: "Business Manager", ja: "経営・管理" },
  { value: "working_holiday", en: "Working Holiday", ja: "ワーキングホリデー" },
  { value: "other", en: "Other", ja: "その他" },
];

const EMPLOYMENT_OPTIONS: { value: ApplicantProfile["employment_status"]; en: string; ja: string }[] = [
  { value: "seishain", en: "Full-time employee", ja: "正社員" },
  { value: "keiyaku", en: "Contract employee", ja: "契約社員" },
  { value: "haken", en: "Temp/dispatch worker", ja: "派遣社員" },
  { value: "self_employed", en: "Self-employed", ja: "自営業" },
  { value: "student", en: "Student", ja: "学生" },
  { value: "job_offer", en: "Job offer (not started)", ja: "内定" },
  { value: "unemployed", en: "Unemployed", ja: "無職" },
];

export default function ProfileForm({
  profile,
  onChange,
}: {
  profile: ApplicantProfile;
  onChange: (p: ApplicantProfile) => void;
}) {
  const { lang, t } = useLanguage();
  const [open, setOpen] = useState(false);

  const set = <K extends keyof ApplicantProfile>(key: K, value: ApplicantProfile[K]) =>
    onChange({ ...profile, [key]: value });

  return (
    <div className="card">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <span className="text-sm font-medium">{t("profileTitle")}</span>
        <span className="text-xs text-ink/60 dark:text-ink-dark/60">
          {open ? t("profileHide") : t("profileEdit")}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 grid grid-cols-2 gap-3 text-sm border-t border-rule dark:border-rule-dark pt-3">
          <Field label={t("fieldNationality")}>
            <input
              className="input"
              value={profile.nationality}
              onChange={(e) => set("nationality", e.target.value)}
            />
          </Field>

          <Field label={t("fieldVisaType")}>
            <select
              className="input"
              value={profile.visa_type}
              onChange={(e) => set("visa_type", e.target.value as ApplicantProfile["visa_type"])}
            >
              {VISA_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o[lang]}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t("fieldEmployment")}>
            <select
              className="input"
              value={profile.employment_status}
              onChange={(e) =>
                set("employment_status", e.target.value as ApplicantProfile["employment_status"])
              }
            >
              {EMPLOYMENT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o[lang]}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t("fieldIncome")}>
            <input
              type="number"
              className="input tabular-figures"
              value={profile.annual_income_jpy ?? ""}
              onChange={(e) => set("annual_income_jpy", e.target.value ? Number(e.target.value) : null)}
            />
          </Field>

          <Field label={t("fieldJapanese")}>
            <select
              className="input"
              value={profile.japanese_level}
              onChange={(e) =>
                set("japanese_level", e.target.value as ApplicantProfile["japanese_level"])
              }
            >
              <option value="none">{lang === "ja" ? "なし" : "None"}</option>
              <option value="n5">N5</option>
              <option value="n4">N4</option>
              <option value="n3">N3</option>
              <option value="n2">N2</option>
              <option value="n1">N1</option>
              <option value="native">{lang === "ja" ? "ネイティブ" : "Native"}</option>
            </select>
          </Field>

          <Field label={t("fieldHousehold")}>
            <input
              type="number"
              min={1}
              className="input tabular-figures"
              value={profile.household_size}
              onChange={(e) => set("household_size", Number(e.target.value))}
            />
          </Field>

          <label className="flex items-center gap-2 col-span-2">
            <input
              type="checkbox"
              checked={profile.guarantor_available}
              onChange={(e) => set("guarantor_available", e.target.checked)}
            />
            {t("fieldGuarantor")}
          </label>

          <label className="flex items-center gap-2 col-span-2">
            <input
              type="checkbox"
              checked={profile.emergency_contact_in_japan}
              onChange={(e) => set("emergency_contact_in_japan", e.target.checked)}
            />
            {t("fieldEmergencyContact")}
          </label>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-ink/60 dark:text-ink-dark/60">{label}</span>
      {children}
    </label>
  );
}
