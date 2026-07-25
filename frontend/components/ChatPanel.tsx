"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/i18n";

export default function ChatPanel({
  onSend,
  loading,
  clarifyQuestion,
}: {
  onSend: (message: string) => void;
  loading: boolean;
  clarifyQuestion: string | null;
}) {
  const { t } = useLanguage();
  const [text, setText] = useState(
    "Something in Shinjuku under ¥150,000, 1K or 1DK, near a train line"
  );

  const submit = () => {
    if (!text.trim() || loading) return;
    onSend(text.trim());
  };

  return (
    <div className="flex flex-col gap-3">
      {clarifyQuestion && (
        <div className="card px-4 py-3 text-sm">
          <span className="font-medium">{t("ekidenAsks")}</span> {clarifyQuestion}
        </div>
      )}
      <textarea
        className="input min-h-[88px] resize-none"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t("chatPlaceholder")}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
        }}
      />
      <button className="btn-primary self-start" onClick={submit} disabled={loading}>
        {loading ? t("btnSearching") : clarifyQuestion ? t("btnAnswer") : t("btnFind")}
      </button>
      <p className="text-xs text-ink/50 dark:text-ink-dark/50">{t("chatHint")}</p>
    </div>
  );
}
