"use client";

import { CheckCircleIcon, PinIcon, ShieldIcon, YenIcon } from "./Icons";

/** Static mockup shown in the hero — proves the payoff before the user searches anything. */
export default function CostRevealDemo() {
  return (
    <div className="float-slow card p-5 w-full max-w-sm bg-white/90 dark:bg-white/[0.05] backdrop-blur">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5 text-xs text-ink/50 dark:text-ink-dark/50">
          <PinIcon size={13} />
          Shinjuku, Tokyo · 1K
        </div>
        <span className="pill bg-orange-500/10 text-orange-700 dark:text-orange-400">SUUMO</span>
      </div>

      <div className="flex items-baseline gap-3 border-y border-rule dark:border-rule-dark py-3 mb-3">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-ink/50 dark:text-ink-dark/50">
            Advertised
          </div>
          <div className="tabular-figures line-through text-ink/40 dark:text-ink-dark/40 text-sm">
            ¥98,000
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-ink/50 dark:text-ink-dark/50">
            Actually
          </div>
          <div className="tabular-figures text-2xl font-bold text-signal">
            ¥121,400<span className="text-xs font-normal ml-1 text-ink/60 dark:text-ink-dark/60">/mo</span>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-2 text-xs">
        <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
          <ShieldIcon size={14} /> No bait-listing signals found
        </div>
        <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
          <CheckCircleIcon size={14} /> Guarantor company accepts foreign nationals
        </div>
        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
          <YenIcon size={14} /> Requires Japan-based emergency contact
        </div>
      </div>
    </div>
  );
}
