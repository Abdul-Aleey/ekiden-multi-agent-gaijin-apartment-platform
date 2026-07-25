export interface ProgressStep {
  label: string;
  status: "pending" | "active" | "done";
  detail?: string;
}

function StepIcon({ status }: { status: ProgressStep["status"] }) {
  if (status === "done") {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-signal text-white text-[11px]">
        ✓
      </span>
    );
  }
  if (status === "active") {
    return (
      <span className="relative flex h-5 w-5 items-center justify-center">
        <span className="absolute h-5 w-5 rounded-full border-2 border-indigo-400/30" />
        <span className="absolute h-5 w-5 rounded-full border-2 border-t-indigo-500 border-r-indigo-500 border-b-transparent border-l-transparent animate-spin" />
      </span>
    );
  }
  return <span className="flex h-5 w-5 items-center justify-center rounded-full border border-rule dark:border-rule-dark" />;
}

export default function SearchProgress({ steps }: { steps: ProgressStep[] }) {
  return (
    <div className="card p-4 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-indigo-500 via-violet-500 to-signal animate-pulse" />
      <ol className="space-y-3">
        {steps.map((step, i) => (
          <li key={i} className="flex items-start gap-3">
            <StepIcon status={step.status} />
            <div className="flex-1">
              <p
                className={
                  "text-sm " +
                  (step.status === "pending"
                    ? "text-ink/40 dark:text-ink-dark/40"
                    : step.status === "active"
                    ? "font-medium"
                    : "text-ink/70 dark:text-ink-dark/70")
                }
              >
                {step.label}
              </p>
              {step.detail && (
                <p className="text-xs text-ink/50 dark:text-ink-dark/50 mt-0.5">{step.detail}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
