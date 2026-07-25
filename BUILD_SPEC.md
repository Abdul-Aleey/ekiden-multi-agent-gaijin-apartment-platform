# Ekiden — Build Spec

*Ekiden (駅伝) — the relay race: no single runner covers the whole distance, each leg hands off to the next. That's the agent pipeline here: preference-gathering hands to search, search hands to analysis, analysis hands to the inquiry writer.*

Hand this file to Claude Code. It is the complete engineering brief.

---

## 0. Rules of engagement

**Context.** Agent Forge AI Hackathon Tokyo (ハッカソン東京), Minato City. Team formation/project setup starts 11:30, **submission deadline 16:00**, live demos 3 minutes per team, winners announced 17:30.

**Required stack rule (judged at code level):** must use at least one of **ai&, Daytona, GMI Cloud, Nosana, Qwen Cloud, Qoder**. This spec uses four — ai&, GMI Cloud, Qwen Cloud, Daytona — each for a reason stated out loud in the demo, not box-ticking.

**Theme rule:** must be "an AI agent or swarm of agents that solves a real-world problem through the lens of Tokyo and Japanese creativity." This product is grounded in a real, specific Tokyo problem: foreign residents renting apartments.

**Hard rule: deploy a working skeleton within the first hour.** Everything after is incremental deploys. A beautiful local app is worth zero — projects must deploy live, not localhost-only.

**Judging criteria, in the order they matter here:**
1. Theme alignment — rooted in Japan
2. Innovation
3. Real-life problem solving
4. Sponsored product usage — verified at code level

---

## 1. The product

Renting an apartment in Japan as a foreigner has four compounding problems:

1. **You don't know where to even start looking.** SUUMO/HOME'S return thousands of results with no sense of which ones would actually accept you, or what they truly cost.
2. **The advertised rent is a lie of omission.** 敷金, 礼金, 仲介手数料, 保証会社初回費用, 火災保険, 鍵交換代 typically add 4–6 months' rent up front. Every listing site sorts by monthly rent, which is the wrong number.
3. **You don't know if you'll be refused.** Many landlords refuse non-Japanese applicants. Listings state their conditions in Japanese free text. Applicants find out after viewing, applying, and waiting — days wasted, and it is humiliating.
4. **You can't write the inquiry.** First contact with a Japanese agency is expected in business keigo.

**The product: Ekiden.** A conversational apartment-finding relay. Tell it what you want (area, budget, layout, must-haves) — it asks a few clarifying questions if needed, then hands off through a chain of agents that search, rank, cost out, and eligibility-check a shortlist, presenting **10 listings with an honest pros/cons read on each**. Pick one, ask follow-up questions, and get a keigo inquiry email ready to send.

### Positioning — say this exactly

Ekiden is **the layer between "I have no idea where to start" and "I'm ready to email this agency."** Not a raw search engine — a relay of specialists that narrows, costs, and vets a shortlist so a foreigner doesn't waste a week finding out the listing was never realistic for them.

### Ethical framing — NON-NEGOTIABLE

The eligibility feature is **applicant-side**, never landlord-side.

- It does **not** predict landlord prejudice. It **extracts requirements the listing already states** (外国人相談可 / 保証人不要 / 国籍不問 / 保証会社利用必須 / 日本語能力) and checks them against the applicant's actual situation.
- **Every eligibility finding must quote the exact source text from the listing.** No quote, no finding.
- Output is always paired with a path forward (guarantor companies that accept foreigners, UR listings, foreigner-friendly agencies). Never end on a refusal.
- Never build or expose a landlord-facing screening view. If asked in Q&A: *"This tells an applicant what a listing already says about itself, so they don't waste a week finding out. It would be useless to a landlord — they already know their own conditions."*

---

## 2. Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind | Deploy in one command |
| Backend | **Python 3.11 + FastAPI** | Async SSE, agent orchestration |
| Frontend host | Vercel | Git push deploys |
| Backend host | Render (or Railway) | Free tier, one-command Python deploy |
| Data | **SQLite, read-only at runtime** | Pre-built corpus (see section 4). No live external calls for listing data. |
| State | Conversation state in-memory per session (no auth, no accounts) | Keeps scope tight; nothing persists across sessions |

Two deploys. Set `NEXT_PUBLIC_API_URL` on Vercel to the Render URL. Configure CORS on FastAPI to allow the Vercel origin **and** localhost.

**Do not** attempt to run FastAPI as a Vercel serverless function. It works, but debugging the ASGI adapter under time pressure is a known time sink.

---

## 3. Scope

### Must have — ship or fail
- Chat-style intake: user states area/budget/preferences in free text; a preference-gathering agent asks up to 2 clarifying questions if critical info is missing (budget or area), then proceeds
- Search agent returns **10 ranked listings** from the pre-built corpus, matched to stated preferences
- Every listing shows **pros and cons**, grounded in data (not generic)
- **True upfront cost + true effective monthly** per listing (not just advertised rent)
- Eligibility read per listing with a quoted source line per finding, relative to a lightweight applicant profile
- Follow-up Q&A: user can ask about any listing in the shortlist and get an answer grounded in that listing's data
- Keigo inquiry email for a chosen listing, copyable
- Deployed, publicly reachable

### Should have
- Bait-listing (おとり物件) trust check per listing
- Progressive/streamed results — sections appear as agents finish
- UR賃貸 alternatives surfaced when eligibility across the shortlist looks poor
- Visa-expiry vs lease-length check

### Could have — only if ahead
- Side-by-side compare of 2 listings from the shortlist
- English gloss under the Japanese email
- 内見 question checklist in Japanese

### Will not have — do not build
Auth. User accounts. Saved history across sessions. Live scraping of suumo/homes.co.jp. Landlord-facing anything. Mobile-specific layout. Multi-language beyond JA/EN.

---

## 4. Data — live search across multiple sites, with a real fallback corpus

**Primary path: live fetch against multiple listing sites in parallel — HOME'S and SUUMO.** Both verified during spec-writing with real fetches returning real listing cards (rent, layout, address), no captcha:
- HOME'S: `https://www.homes.co.jp/chintai/tokyo/{ward-romaji}-city/list/`
- SUUMO: `https://suumo.jp/chintai/tokyo/sc_{ward-romaji}/`

Fetch both concurrently per search, merge, **dedupe**, then rank. More sources = better coverage and resilience (if one site is slow/blocked, the other still contributes). Accepted tradeoff, stated openly in the demo (section 11): this is automated access against both sites' ToS. A single-endpoint fetch per site per search, not a crawler.

**Fallback path: a pre-built real Tokyo corpus.** If both live fetches fail, time out, or return zero parseable results, the Search Agent falls back silently to a small hand-built SQLite corpus of real Tokyo listings, so the shortlist never comes back empty on stage. This corpus is the safety net, not the primary source — see 4.3.

### 4.1 Live fetch — `services/live_search.py`

```python
async def search_live(ward: str, max_budget_jpy: int | None, layout: str | None, timeout_s: float = 8.0) -> list[Listing]:
    """
    Run search_homes_live(ward, ...) and search_suumo_live(ward, ...) concurrently via asyncio.gather(..., return_exceptions=True).
    Each: build the site's ward search URL, fetch with a normal User-Agent, `timeout_s` budget,
    strip HTML with BeautifulSoup, extract listing cards as text blocks (not full markdown dump),
    pass to Qwen for structured extraction into Listing[].
    If BOTH sites raise/timeout/return zero cards: raise LiveSearchError — orchestrator calls the fallback corpus.
    If only one succeeds: proceed with that one's results, note the other's absence in an assumption.
    """
```

- Confirm the exact ward-slug mapping for both sites for the wards you actually demo against — check 2–3 by hand before relying on them live (slugs differ between the two sites, e.g. HOME'S uses `shinjuku-city`, SUUMO uses `sc_shinjuku`).
- Extraction must still populate `conditions_text` and `raw_flags` per section 4.5's rules — if a live page's fields are too sparse for a good eligibility read, that listing is weaker but not excluded; note sparsity rather than inventing detail.
- **One retry only** per site on timeout, then drop that site's results for this search. Never retry-loop against a live external site during a demo.

### 4.2 Dedup — `services/dedup.py`

Two sites listing the same physical unit is the norm (agencies cross-post). Before ranking, dedupe the merged HOME'S + SUUMO + fallback-corpus results so the shortlist never shows the same apartment twice.

```python
def dedupe_listings(listings: list[Listing]) -> list[Listing]:
    """
    Group by a fuzzy key: normalized building name (strip whitespace/full-width chars)
    + rent_jpy rounded to nearest 1000 + layout + floor (when available).
    Within a group, keep the record with the most complete conditions_text
    (longest non-null text) — richer source data wins for the eligibility read.
    Prefer live-sourced records over fallback-corpus records when both match,
    since live is fresher, but merge raw_flags from both if they differ.
    """
```

- This is a real, code-level piece of logic — call it out in the demo as what keeps the 10 results non-redundant across two independent live sources plus the fallback.
- If building name isn't cleanly extractable, fall back to `(ward, nearest_station, rent_jpy±2000, layout)` as the fuzzy key.

### 4.2 `listings.sqlite` — the fallback corpus

Single table `listings`, schema below. Populated from **real** sources only — never fabricated rows. This is what the Search Agent uses when live fetch fails.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | stable hash of source + source_id |
| `source` | TEXT **required** | `"ur"` \| `"manual"` — where this row actually came from |
| `source_url` | TEXT | |
| `fetched_at` | TEXT **required** | ISO date |
| `title` | TEXT | |
| `address` | TEXT | |
| `ward` | TEXT | normalized, e.g. `"世田谷区"` |
| `nearest_station` | TEXT | |
| `line` | TEXT | |
| `walk_minutes` | INTEGER | |
| `layout` | TEXT | `"1K"`, `"2LDK"` — normalized uppercase |
| `area_sqm` | REAL | |
| `building_year` | INTEGER | |
| `floor` | TEXT | |
| `rent_jpy` | INTEGER **required** | monthly, excluding 管理費 |
| `kanrihi_jpy` | INTEGER | default 0 |
| `shikikin_months`, `reikin_months` | REAL | null = unknown, 0.0 = stated zero — keep distinct |
| `hoshou_gaisha_required` | INTEGER | 0/1/null |
| `conditions_text` | TEXT | **critical** — verbatim 備考/入居条件/取引条件 block, never summarized |
| `raw_flags` | TEXT | JSON array of exact matched phrases (see list in section 4.4) |
| `posted_date` | TEXT | |
| `raw_blob` | TEXT | full original record as JSON |

**Realistic volume for a fallback (doesn't need to be huge — it only shows up if live fails):** target **60–150 real rows**. Composition:
- **Real UR賃貸 properties** (40–80 rows) — public data from UR's own site, no ToS issue, `source="ur"`. UR rows also double as the "no guarantor, no key money" alternative shown when eligibility looks poor — surfaced regardless of whether live or fallback served the shortlist.
- **Real manually-collected listings** (20–70 rows) — pages saved by hand (normal browsing, not automated) into `data/manual/`, parsed by a `ManualProvider`. This is the operator's own research, not a bot.

If volume lands under 100, note it in `data/README.md`. This corpus is insurance, not the headline — most demo runs should hit live HOME'S successfully and never touch it.

### 4.3 `benchmarks.json` — ward rent context

Real government data, no registration needed:
- **Tokyo Metropolitan Government / e-Stat 住宅・土地統計調査** — ward-level rent statistics, downloadable now as CSV/Excel.
- **MLIT 不動産情報ライブラリ** — CSV download of transaction/land price data works immediately without an API key (the API key itself takes ~5 business days, skip it for tonight).

Used for: the price-outlier trust signal, and to contextualize a listing's rent against its ward even when the corpus has few comparable rows in that ward.

### 4.4 `ur_properties.json` and `guarantor_companies.json`

Same as before: UR sample also feeds `listings` directly (see 4.1); `guarantor_companies.json` is ~8 hand-curated entries verified from each company's own site — null where unverifiable, never guessed.

### 4.5 Normalization rules (apply on ingest — and on live-fetched records before use)

- 万円 → integer yen. `8.5万円` → `85000`.
- `礼金2ヶ月` → `reikin_months=2.0`.
- `敷金なし` / `礼金ゼロ` → `0.0`, not null.
- Layout uppercase, no spaces: `1LDK`.
- `raw_flags`: extract only exact phrase matches: `外国人相談可`, `外国人可`, `国籍不問`, `保証人不要`, `保証人不在可`, `保証会社必須`, `保証会社利用可`, `緊急連絡先必須`, `日本語`, `留学生可`, `法人契約`, `女性限定`, `二人入居可`, `事務所利用可`.
- **Never invent a value.** Absent field → null.

### 4.6 CLI — builds the fallback corpus only (live path needs no CLI, it runs per-request)

```bash
python -m data_loader --all
python -m data_loader --ur
python -m data_loader --manual
python -m data_loader --benchmarks
python -m data_loader --validate
```

`--validate` reports row count, null rate per column, ward/layout distribution, and outlier rents. Every run appends to `data/README.md`: date, sources, counts, assumptions. Re-running never duplicates rows.

---

## 5. Architecture — the relay

```
Client (Next.js)
   │  POST /api/chat  (SSE stream, conversational turn-by-turn)
   ▼
Orchestrator (FastAPI)
   │
   ├─ 0. Preference Agent     → Qwen      (extract structured prefs from free text; asks clarifying Qs)
   ├─ 1. Search & Rank Agent  → Qwen      (live fetch HOME'S + SUUMO in parallel, dedupe, fallback to corpus if both fail, rank → top 10)
   ├─ 2. Cost Auditor         → Daytona   (arithmetic per listing, in sandbox)
   ├─ 3. Trust Checker        → GMI       (independent model, per listing)
   ├─ 4. Eligibility Analyst  → Qwen      (evidence-quoted findings per listing)
   └─ 5. Inquiry Writer       → ai&       (keigo generation, on-demand for a chosen listing)
```

**Sequencing per turn:**
1. Preference Agent runs first. If required fields (area, budget) are missing, it returns a clarifying question instead of proceeding — **max 2 rounds of clarification**, then proceed with best-effort defaults (stated as assumptions).
2. Search & Rank Agent runs once prefs are sufficient: fetches HOME'S + SUUMO concurrently for the target ward, dedupes the merged results (section 4.2), falls back to the local corpus if both live fetches fail, then ranks → top 10.
3. For the top 10, **Cost, Trust, and Eligibility run concurrently per listing** with `asyncio.gather`, batched to keep latency down (e.g. batch of 10 in parallel, not sequential).
4. Pros/cons per listing is synthesized from the Cost + Trust + Eligibility outputs — not a separate agent call, just a deterministic merge, to avoid a 6th agent hop.
5. Inquiry Writer runs only when the user picks a listing — not for all 10 up front.
6. Follow-up questions on a specific listing route back through a lightweight Q&A agent (Qwen) with that listing's full record as context — no corpus-wide re-search needed.

**Streaming:** emit an SSE event as each stage completes so the UI fills in progressively — the clarifying question, then the 10-card shortlist, then per-card cost/trust/eligibility as they land.

---

## 6. Backend

### Layout

```
backend/
  main.py                  # FastAPI app, CORS, SSE routes
  config.py                # env vars, provider registry
  schemas.py               # ALL Pydantic models — single source of truth
  orchestrator.py           # turn sequencing, asyncio.gather, SSE events
  agents/
    __init__.py
    preference.py
    search.py
    cost.py
    trust.py
    eligibility.py
    inquiry.py
    followup.py
  providers/
    __init__.py
    client.py              # OpenAI-compatible async client
    registry.py             # name -> (base_url, key, model)
  services/
    live_search.py           # HOME'S + SUUMO concurrent fetch, per section 4.1
    dedup.py                 # cross-source + fallback dedup, per section 4.2
    corpus.py                # SQLite read layer over listings.sqlite (fallback)
    daytona.py               # sandbox execution client
  prompts/
    preference.py
    search.py
    trust.py
    eligibility.py
    inquiry.py
    followup.py
  data/
    listings.sqlite
    benchmarks.json
    ur_properties.json
    guarantor_companies.json
  requirements.txt
```

`requirements.txt`: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `httpx`, `sse-starlette`, `python-dotenv`, `beautifulsoup4`, `lxml`

### Provider abstraction — build this first

Base URLs, model strings and auth headers for Qwen Cloud, GMI Cloud, ai& and Daytona are **not** in this spec and **must not be guessed**. Get them from the 10:45 tech workshop and sponsor docs.

Most expose an OpenAI-compatible `/chat/completions`. Write one async client against that shape; adapt only where a provider differs.

```python
# providers/registry.py
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Provider:
    base_url: str
    api_key: str
    model: str

REGISTRY = {
    "qwen":  Provider(os.environ["QWEN_BASE_URL"],  os.environ["QWEN_API_KEY"],  os.environ["QWEN_MODEL"]),
    "gmi":   Provider(os.environ["GMI_BASE_URL"],   os.environ["GMI_API_KEY"],   os.environ["GMI_MODEL"]),
    "aiand": Provider(os.environ["AIAND_BASE_URL"], os.environ["AIAND_API_KEY"], os.environ["AIAND_MODEL"]),
}
```

```python
# providers/client.py
async def complete_json(provider: str, system: str, user: str, schema_hint: str) -> dict:
    """
    POST to {base_url}/chat/completions.
    Force JSON output. Strip ```json fences before parsing.
    On JSONDecodeError: retry ONCE with the parse error appended to the user message.
    On second failure: raise AgentError — orchestrator degrades gracefully.
    """
```

**Every agent call must degrade gracefully.** If one agent fails for one listing, the other listings and stages still render. Never let a single failure blank the page.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Uptime check |
| POST | `/api/chat` | **Main.** One conversational turn — SSE stream of clarifying Q, shortlist, or per-listing analysis |
| POST | `/api/listing/{id}/followup` | Ask a question about a specific shortlisted listing |
| POST | `/api/listing/{id}/inquiry` | Generate the keigo email for a chosen listing |

### SSE event contract

```
event: stage        data: {"stage":"preferences","status":"running"}
event: clarify       data: {"question":"..."}                 # if more info needed
event: shortlist     data: {"listings":[...Listing x10]}
event: cost          data: {"listing_id":"...", ...CostBreakdown}
event: trust         data: {"listing_id":"...", ...TrustReport}
event: eligibility   data: {"listing_id":"...", ...EligibilityReport}
event: error         data: {"stage":"trust","listing_id":"...","message":"..."}
event: done          data: {"elapsed_ms":12400}
```

---

## 7. Schemas — `schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date

VisaType = Literal[
    "engineer_specialist", "student", "permanent", "spouse_of_japanese",
    "dependent", "specified_skilled", "business_manager", "working_holiday", "other",
]

class ApplicantProfile(BaseModel):
    nationality: str
    visa_type: VisaType
    visa_expiry: Optional[date]
    employment_status: Literal["seishain","keiyaku","haken","self_employed","student","job_offer","unemployed"]
    annual_income_jpy: Optional[int]
    japanese_level: Literal["none","n5","n4","n3","n2","n1","native"]
    guarantor_available: bool
    emergency_contact_in_japan: bool
    household_size: int = 1

class SearchPreferences(BaseModel):
    area_or_ward: Optional[str]
    max_budget_jpy: Optional[int]
    layout: Optional[str]
    min_area_sqm: Optional[float]
    max_walk_minutes: Optional[int]
    must_haves: list[str] = []          # free text, e.g. "pet ok", "near JR line"
    missing_critical_fields: list[str]  # populated by Preference Agent if area/budget absent

class Listing(BaseModel):
    id: str
    source: Literal["ur","manual"]
    source_url: Optional[str]
    title: str
    address: str
    ward: Optional[str]
    nearest_station: Optional[str]
    walk_minutes: Optional[int]
    layout: Optional[str]
    area_sqm: Optional[float]
    rent_jpy: int
    kanrihi_jpy: int = 0
    conditions_text: str
    raw_flags: list[str]

class CostBreakdown(BaseModel):
    advertised_monthly_jpy: int
    upfront_total_jpy: int
    effective_monthly_jpy: int
    markup_percent: float
    assumptions: list[str]

class TrustSignal(BaseModel):
    code: Literal["price_outlier","stale_posting","vague_address","missing_fees","no_property_id"]
    severity: Literal["high","medium","low"]
    explanation_en: str
    evidence: str

class TrustReport(BaseModel):
    risk: Literal["clear","caution","high_risk"]
    signals: list[TrustSignal]

class EligibilityFinding(BaseModel):
    requirement_ja: str
    requirement_en: str
    verdict: Literal["pass","concern","blocker"]
    quoted_line: str        # MUST be a verbatim substring of conditions_text
    advice_en: str

class Alternative(BaseModel):
    kind: Literal["ur","guarantor_company"]
    name: str
    why_en: str
    url: Optional[str]

class EligibilityReport(BaseModel):
    outlook: Literal["likely","uncertain","unlikely"]
    confidence_note: str
    findings: list[EligibilityFinding]
    alternatives: list[Alternative]

class ListingCard(BaseModel):
    listing: Listing
    cost: CostBreakdown
    trust: TrustReport
    eligibility: EligibilityReport
    pros: list[str]
    cons: list[str]

class InquiryEmail(BaseModel):
    subject_ja: str
    body_ja: str
    body_en_gloss: str

class ChatTurnRequest(BaseModel):
    message: str
    profile: ApplicantProfile
    prior_prefs: Optional[SearchPreferences] = None
```

---

## 8. Agent specifications

### 8.1 Preference Agent — Qwen

**Input:** free-text user message + any `prior_prefs` from earlier turns. **Output:** `SearchPreferences`.

- Extracts area/ward, budget, layout, must-haves from natural language ("something near Shinjuku under 120,000, pet-friendly").
- If `area_or_ward` or `max_budget_jpy` is missing, populate `missing_critical_fields` and the orchestrator emits a `clarify` event instead of searching. **Max 2 clarification rounds** — after that, proceed with stated defaults and list them as assumptions.
- Never invents a preference the user didn't state or imply.

### 8.2 Search & Rank Agent — Qwen, over live + fallback data

**Input:** `SearchPreferences`. **Pipeline:**

1. Call `services/live_search.py::search_live(ward, ...)` — HOME'S + SUUMO concurrently, `timeout_s=8.0`.
2. If it raises `LiveSearchError` (both sites failed), query `services/corpus.py` instead (SQL-filtered by ward/budget/layout).
3. Merge whatever succeeded (live results, or corpus results, or live-from-one-site + corpus as extra candidates if the other site failed) and run `services/dedup.py::dedupe_listings`.
4. Pass the deduped candidate list (not the raw unfiltered set) to Qwen for ranking against `SearchPreferences` — layout/budget/must-haves match quality, not just recency.
5. Return exactly 10 `Listing`s (or fewer if genuinely fewer good matches exist — never pad with irrelevant rows). For each, a one-line reason it was picked, grounded in the actual row data.

Emit which path served the results (`"live"`, `"live_partial"`, or `"fallback"`) as part of the `shortlist` SSE event — useful for the demo talk track and for debugging on stage if something looks off.

### 8.3 Cost Auditor — Daytona sandbox

Same arithmetic model as before, run per listing:

```
upfront   = shikikin + reikin + chukai(+tax) + hoshou_initial + kasai_hoken + kagi_koukan + first month rent + kanrihi
effective_monthly = (upfront + (rent + kanrihi) * 23 + hoshou_annual*2 + koushinryou) / 24
markup_percent    = (effective_monthly / advertised_monthly - 1) * 100
```

Runs as generated Python inside a Daytona sandbox — real code-level integration, defensible on stage. Defaults when unstated (list every one in `assumptions`): 保証会社 initial 50% of one month, annual ¥10,000; 火災保険 ¥20,000/2yr; 鍵交換 ¥22,000; 更新料 1 month at month 24; 仲介手数料 1 month + 10% tax.

**Fail loudly, not silently.** Sandbox unreachable → compute locally, note it in `assumptions`, never blank the section.

### 8.4 Trust Checker — GMI

Independent model, deliberately different from Qwen — reduces one model's blind spot propagating into both search ranking and trust. Say that on stage.

Signals: `price_outlier` (vs `benchmarks.json` ward median for the layout), `stale_posting`, `vague_address`, `missing_fees`, `no_property_id`. Two or more high-severity → `high_risk`.

### 8.5 Eligibility Analyst — Qwen

**Hard constraint: `quoted_line` must be a verbatim substring of `conditions_text`.** Validate server-side with `in`. Retry once with the error fed back; drop the finding if it fails again.

Check in order: nationality/foreigner conditions → guarantor requirement vs profile → emergency contact requirement → Japanese level → income vs rent (rent ≤ 1/3 income) → visa expiry vs typical 2-year lease.

`alternatives` mandatory whenever outlook is `uncertain`/`unlikely` — UR listings from the corpus (`source="ur"`) and guarantor companies from `guarantor_companies.json`.

### 8.6 Pros/Cons synthesis — deterministic, no extra agent

Merged in the orchestrator from Cost + Trust + Eligibility outputs (e.g. low markup% → pro, `high_risk` trust → con, `blocker` eligibility finding → con with the quoted line attached). Keeps this a 5-agent system, not 6.

### 8.7 Follow-up Q&A — Qwen

**Input:** user question + the specific `ListingCard` already computed. Answers grounded only in that listing's fields — never introduces facts not present in the record. If the answer isn't derivable from the data, say so plainly rather than guessing.

### 8.8 Inquiry Writer — ai&

Generated only when the user picks a listing. Japanese-hosted generation — real argument, not a sponsor plug: input includes nationality, visa status, income (sensitive personal data); ai& keeps generation in Japan.

- Correct 敬語 business register, ~250–350 characters.
- States 内見希望, move-in timing, household size.
- **Proactively addresses the top eligibility concern** from that listing's `EligibilityReport`.
- Never mentions nationality unless it helps.
- `body_en_gloss`: plain-English explanation.

---

## 9. Frontend

### Design direction

**Subject:** Japanese property paperwork — 物件資料, ruled tables, 万円 notation, tabular figures.

**Audience:** a foreigner in Japan, currently overwhelmed by "where do I even start," about to be shown a shortlist they can actually trust.

**Avoid:** cream+serif+terracotta AI-default look; near-black+neon-accent look; broadsheet-with-hairlines look.

**Direction:** cold paper-white ground, ink-navy text, ruled structure borrowed from a 物件資料 table. One signal red, reserved **only** for cost markup and eligibility blockers. Figures in tabular-lining monospace. Bilingual labels, Japanese primary.

**Signature element:** the **shortlist reveal** — 10 cards arriving progressively, each with advertised rent struck through beside the true effective monthly, and a compact pros/cons pair. That's the peak demo moment, not any single listing's detail view.

### Layout

**Left — conversation (sticky):**
1. Chat input: free text preferences, clarifying questions appear inline as chat bubbles
2. Profile form (collapsed by default, pre-filled with a realistic demo profile): nationality, visa, employment, income, Japanese level, guarantor, emergency contact
3. "Find apartments"

**Right — results, streaming in:**
1. **Shortlist** — 10 cards, each showing true cost, trust badge, eligibility outlook, pros/cons
2. Click a card → expanded detail: full eligibility findings with quoted lines, follow-up question box, "Draft inquiry email" button
3. **Alternatives** — UR listings / guarantor companies, shown when eligibility across the shortlist skews poor

Each card fills in independently as its SSE events land; a quiet skeleton while pending per card.

### Copy rules

Name things as experienced: "What you'll actually pay," not "computed cost model." Buttons keep their verb through the flow: "Find apartments" → "10 found."

---

## 10. Schedule

| Time | Task | Gate |
|---|---|---|
| 11:30–11:45 | Scaffold both repos, push, connect Vercel + Render | — |
| 11:45–12:30 | `/health` + hardcoded shortlist rendering in the UI → **both deployed live** | **Not live by 12:30 → cut Trust Checker now** |
| 12:30–13:00 | Lunch. Write the six prompts on paper. | — |
| 13:00–13:45 | Corpus loaded into SQLite; Search & Rank Agent returning real top-10; Cost Auditor via Daytona | — |
| 13:45–14:15 | Eligibility Analyst + `quoted_line` validator, per listing | Behind → cut Trust |
| 14:15–14:45 | Inquiry Writer via ai& + follow-up Q&A + UR alternatives | Behind → cut alternatives |
| 14:45–15:15 | Shortlist streaming polish, demo profile prefill, pros/cons merge | — |
| 15:15–15:45 | **Stop coding.** Rehearse 3× with a timer. Record backup video. | Hard stop regardless of state |
| 15:45–16:00 | Submit. Buffer. | — |

**Cut order when behind:** Trust Checker → follow-up Q&A → UR alternatives → visa-expiry check → English gloss.
**Never cut:** true cost, the quoted-line rule, the 10-listing shortlist, the Japanese email.

---

## 11. Demo script (3 min)

- **0:00–0:25** — "If you're not Japanese, apartment hunting here means not knowing where to start, not knowing the real cost, and not knowing if you'll be refused. Ekiden is a relay of agents that runs that whole search for you."
- **0:25–0:45** — Type a real preference in chat: "something near Shinjuku, under ¥130,000, pet-friendly." Profile pre-filled.
- **0:45–1:30** — Shortlist streams in, 10 cards. **Peak: true cost reveal on card 1** — *"advertised ¥98,000. Actually ¥121,000 a month."*
- **1:30–2:10** — Open one card's eligibility. Point at a quoted Japanese line: *"we're not guessing — the listing says this."* Ask a follow-up question about that listing live.
- **2:10–2:40** — Draft the keigo email for that listing. If a Japanese speaker is judging, ask them to confirm it reads naturally.
- **2:40–3:00** — Sponsor stack, one breath: Qwen for preference extraction, search ranking and eligibility; GMI as an independent model for trust; ai& for keigo because this carries visa/income data and generation stays in Japan; Daytona sandboxing the cost model.

**Have answers ready:**
- *"Isn't this discriminatory?"* → It reads conditions the listing already publishes, to the applicant, so they don't waste a week. Useless to a landlord.
- *"How accurate is eligibility?"* → Every finding quotes the listing. It doesn't predict individual landlords, and says so.
- *"Do you scrape SUUMO/HOME'S live?"* → Yes, live fetch against both per search, deduped across sources. If either site is unreachable mid-demo, it falls back to a real hand-built Tokyo corpus (UR public data + manually collected listings) so the shortlist never comes back empty. Production would formalize this with a data partnership or licensed feed.
- *"Where does the fallback corpus come from?"* → Name the real sources: UR's own site, hand-saved listing pages, MLIT and Tokyo Metropolitan Government rent statistics for ward benchmarks.
- *"How do you avoid showing the same apartment twice from two sites?"* → Point at the dedup step — fuzzy-matched on building name, rent, and layout before ranking.

---

## 12. Failure modes to design against

1. **One agent fails, whole page blanks.** → try/except per agent per listing, partial render always.
2. **Ungrounded eligibility findings.** → `quoted_line` substring check, non-negotiable.
3. **Everything arrives at once after 40s.** → SSE, cards render independently.
4. **Search returns fewer than 10 relevant rows.** → Say so in the UI ("8 matches" not padded to 10) rather than showing irrelevant filler.
5. **Both live sites fail or get blocked mid-demo.** → Silent fallback to the local corpus (section 4). Rehearse this path deliberately, not just the happy path — pull the venue wifi cable once in rehearsal and confirm the shortlist still renders.
6. **Two sites return the same apartment.** → Dedup step (4.2) runs before ranking; verify with a rehearsal query that hits a building known to be cross-posted.
7. **Not deployed.** → Deploy at 12:30 and after every meaningful change.
8. **Venue wifi dies.** → Record a full backup video at 15:30.
9. **Model returns prose instead of JSON.** → Force JSON, strip fences, one retry with the parse error fed back.

---

## 13. Environment

**Backend (Render):**
```
QWEN_BASE_URL=
QWEN_API_KEY=
QWEN_MODEL=
GMI_BASE_URL=
GMI_API_KEY=
GMI_MODEL=
AIAND_BASE_URL=
AIAND_API_KEY=
AIAND_MODEL=
DAYTONA_API_KEY=
DAYTONA_BASE_URL=
ALLOWED_ORIGINS=https://<your-app>.vercel.app,http://localhost:3000
```

**Frontend (Vercel):**
```
NEXT_PUBLIC_API_URL=https://<your-service>.onrender.com
```

Set these **before** the first deploy, not after.

---

## 14. Pre-flight checklist

- [ ] Both repos deployed, `/health` returns 200 from the Vercel origin
- [ ] CORS verified from the deployed frontend, not just localhost
- [ ] `listings.sqlite` fallback corpus has ≥60 real rows, `source` populated for every row
- [ ] Live search rehearsed against both HOME'S and SUUMO for the exact ward you'll demo
- [ ] Fallback path rehearsed at least once (simulate both sites failing) — shortlist still renders
- [ ] Demo profile pre-filled; one demo preference string rehearsed
- [ ] `quoted_line` validator confirmed rejecting a fabricated quote
- [ ] Cost arithmetic checked by hand against one listing
- [ ] Keigo email read by a Japanese speaker at the venue
- [ ] Backup video recorded
- [ ] Submission form completed before 16:00
