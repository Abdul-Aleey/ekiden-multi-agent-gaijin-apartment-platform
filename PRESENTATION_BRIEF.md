# Ekiden — Presentation Content Brief

> **Instructions for the AI generating the deck**: Use the content below to build a
> presentation (PowerPoint or PDF) for a hackathon judge/investor audience. Suggested
> length: 10-12 slides. One major heading below ≈ one slide, except "Agentic
> Architecture" which should be 2-3 slides (one overview diagram, one per pipeline
> stage group). Prefer bullets over paragraphs, keep numbers and quotes exact as
> given. A suggested slide-by-slide outline is at the end of this document.

---

## 1. Project Title & One-Liner

**Ekiden 駅伝** — *"Know before you sign."*

An AI agent relay that helps foreign residents rent apartments in Japan — searches
live listings nationwide, reveals the true cost beyond advertised rent, checks
bait-listing risk, reads your eligibility straight from what each listing actually
says, and drafts the negotiation strategy and the first contact email.

Built for the **Agent Forge AI Hackathon Tokyo**, under the theme *"an AI agent or
swarm of agents that solves a real-world problem through the lens of Tokyo and
Japanese creativity."*

---

## 2. The Real-World Problem

Renting an apartment in Japan as a foreigner has four compounding problems:

1. **You don't know where to even start looking.** Listing sites return thousands
   of results with no sense of which ones would actually accept you, or what they
   truly cost.
2. **The advertised rent is a lie of omission.** Security deposit (敷金), key money
   (礼金), agency fee (仲介手数料), guarantor company fees (保証会社初回費用),
   fire insurance, key exchange — these typically add 4-6 months' rent up front,
   and every listing site sorts by the one number that hides all of this.
3. **You don't know if you'll be refused.** Many landlords have conditions around
   nationality, guarantors, or Japanese ability. Listings state these conditions in
   Japanese free text. Applicants often find out only after viewing, applying, and
   waiting — days wasted, and it can be humiliating.
4. **You can't write the inquiry.** First contact with a Japanese agency is
   expected in formal business Japanese (keigo), which most foreign applicants
   simply cannot produce.

**Ekiden is the layer between "I have no idea where to start" and "I'm ready to
email this agency."** Not a raw search engine — a relay of specialists that
narrows, costs, and vets a shortlist so a foreigner doesn't waste a week finding
out a listing was never realistic for them.

---

## 3. Ethical Framing (worth a slide — judges ask about this)

The eligibility feature is **applicant-side, never landlord-side**:

- It does **not** predict landlord prejudice or bias.
- It **extracts requirements the listing already publishes** (foreigner-related
  conditions, guarantor requirements, Japanese level, income conditions) and checks
  them against the applicant's own stated situation.
- **Non-negotiable rule**: every eligibility finding must quote the exact source
  text from the listing. No quote, no finding — nothing is inferred or guessed.
- Every finding is paired with a path forward (alternative guarantor companies that
  accept foreigners, alternative listings) — it never just ends on a refusal.
- There is no landlord-facing version of this feature. It only ever tells an
  applicant what a listing already says about itself.

---

## 4. Innovation Highlights

- **Multi-agent relay architecture** (the "Ekiden" metaphor: a relay race — no
  single runner covers the whole distance, each leg hands off to the next).
- **Live search, not a static dataset** — real-time concurrent fetch against two
  independent listing sites, nationwide (47 prefectures, 1,718 cities/towns/villages),
  not a pre-scraped or synthetic corpus.
- **Radical honesty in cost math** — the system never fabricates a fee it can't
  verify. Any cost component not explicitly stated by a listing is excluded from
  the total and disclosed as "not stated," rather than filled in with an industry
  average. The number shown is a true floor, not a guess.
- **Evidence-grounded eligibility** — every eligibility claim is validated
  server-side against the listing's own verbatim text before being shown; findings
  that can't be matched to real source text are silently dropped.
- **Independent trust verification** — the bait-listing (おとり物件) check
  deliberately runs on a different model vendor than the one doing search ranking,
  so it functions as a genuine second opinion, not the same model marking its own
  homework.
- **Real sandboxed computation** — the cost arithmetic actually executes inside an
  isolated Daytona cloud sandbox rather than just being trusted inline code.
- **Universal graceful degradation** — every single AI call in the system, across
  every agent, automatically falls back through multiple providers and finally to
  a deterministic rule-based/template result. The product never crashes or shows a
  blank state because one provider is down.
- **Deliberately minimal Japanese in the UI** — since the audience is foreigners,
  the interface itself stays in clean English by default; Japanese is used only
  where it is functionally necessary (verbatim evidence quotes, and the actual
  Japanese email that gets sent).

---

## 5. Agentic Architecture — the Relay

*Ekiden's own metaphor: preference-gathering hands off to search, search hands off
to analysis, analysis hands off to the inquiry writer. Each agent has one job and
passes structured output to the next.*

### Stage 1 — Understanding the request
| Agent | Input | Output | Hands off to |
|---|---|---|---|
| **Preference Agent** | User's free-text message | Structured preferences (area, budget, layout, must-haves) | Area Resolution Agent |
| **Area Resolution Agent** | Free-text location reference | A precisely resolved Japanese prefecture/ward | Search Agent |

If area or budget is still missing, the relay pauses and asks a clarifying
question instead of guessing.

### Stage 2 — Finding candidates
| Agent / Service | Input | Output | Hands off to |
|---|---|---|---|
| **Live Search Service** | Resolved area | Real listings fetched concurrently from two independent sites, deduplicated across sources | Ranking Agent |
| **Ranking Agent** | Candidate pool + preferences | Best-matching shortlist (always 8 listings when the market has that many), each with a plain-language match reason | Per-listing analysis (Stage 3) |

A listing that violates a stated hard constraint (wrong layout, over budget) can
never outrank one that satisfies every constraint — that guarantee is enforced in
code after ranking, not left to the model's judgment.

### Stage 3 — Per-listing analysis (four agents run concurrently for every listing)
| Agent | Input | Output | Feeds into |
|---|---|---|---|
| **Cost Auditor Agent** | One listing's stated fees | Itemized true-cost breakdown: what's included (with real amounts) vs. what's not disclosed | Strategy Advisor |
| **Trust Checker Agent** | Listing data + ward rent benchmarks | Bait-listing risk rating with specific evidence-backed signals | Strategy Advisor |
| **Eligibility Agent** | Listing's conditions text + applicant profile | Pass/concern/blocker findings, each grounded in a verbatim quote from the listing | Strategy Advisor |
| **Strategy Advisor Agent** | The outputs of the three agents above | A concise, listing-specific negotiation and screening-presentation plan | Shown to user |

The Strategy Advisor is deliberately the *last* agent in the chain for a given
listing — it needs to know the real cost gaps, the trust signals, and the specific
eligibility concerns before it can give advice that's actually grounded in that
listing, rather than generic tips.

### Stage 4 — On demand
| Agent | Input | Output |
|---|---|---|
| **Follow-up Q&A Agent** | A specific listing's full data + a free-text question | A direct answer grounded in that listing |
| **Inquiry Email Agent** | Listing + applicant profile + top eligibility concern | A formal Japanese keigo email, plus an English gloss explaining what it says |

Every stage streams to the user in real time as it completes — listings and their
analysis appear progressively, not all at once at the end.

---

## 6. Models & Sponsor Tools — Who Does What, and Why

| Provider / Model | Powers | Why this tier |
|---|---|---|
| **Qwen Cloud** (`qwen3.5-flash`) | Preference extraction, area resolution, search ranking, fee extraction, translation, follow-up Q&A | High-volume, low-latency tasks — a single search calls this many times across a shortlist, so speed matters more than deep reasoning here. Explicitly run in non-reasoning mode to keep latency low. |
| **ai&** (two tiers, one account) | Fast tier: fallback for trust-checking. Quality tier: eligibility analysis, inquiry email, strategy advisor fallback | The quality tier handles the tasks that genuinely benefit from careful multi-step reasoning — validating multiple eligibility criteria against verbatim text, and producing fluent formal Japanese. |
| **GMI Cloud** | Bait-listing trust check (primary), strategy advisor (primary) | Deliberately a *different vendor* from Qwen/ai& — this is what makes the trust check a genuine independent second opinion rather than the same model checking its own ranking decisions. |
| **Daytona** | Executes the true-cost arithmetic inside a real, isolated cloud sandbox | Verifiable, sandboxed computation for the number the whole product is built around — not just "trust me" inline code. |
| **Vertex AI (Gemini, `gemini-3.5-flash`)** | Universal fallback — automatically tried by *every single agent call in the system* if its primary provider is unavailable or fails | Guarantees the product always attempts a real model response before ever falling back to a deterministic/rule-based result, across all four other providers at once. Uses Google Cloud's built-in service-account authentication — no API key to manage. |

Every provider call follows the same pattern: try the best-fit model for the task,
fall back to a secondary real model, then fall back to Vertex AI Gemini, and only
as a last resort fall back to deterministic logic (regex extraction, rule-based
heuristics, or a fixed template) — so the product **never** crashes or blanks out
due to one provider being down.

---

## 7. Deployment

Single Cloud Run service — the Next.js frontend is built as a static export and
served directly by the same FastAPI process that runs the API, so there is exactly
one deployed URL, one container, and no cross-origin complexity between frontend
and backend.

---

## Suggested Slide-by-Slide Outline

1. Title slide — Ekiden 駅伝, tagline, hackathon name
2. The problem (4 compounding issues, section 2 above)
3. The solution / positioning (one sentence + what the product does end to end)
4. Ethical framing (section 3) — short, judges specifically probe this
5. Innovation highlights (section 4) — pick top 4-5 bullets
6. Agentic architecture overview — a simple left-to-right diagram: Preferences →
   Area Resolution → Search → Rank → [Cost / Trust / Eligibility running in
   parallel] → Strategy Advisor → shown to user
7. Agentic architecture detail — the per-listing agent table (section 5, stage 3)
8. Models & sponsor tools table (section 6) — this is the code-verified sponsor
   usage slide
9. What makes the cost number trustworthy (radical honesty + Daytona sandboxing)
10. What makes eligibility trustworthy (verbatim quote requirement)
11. Deployment / architecture footer (section 7)
12. Closing — restate the one-liner and the real problem it solves
