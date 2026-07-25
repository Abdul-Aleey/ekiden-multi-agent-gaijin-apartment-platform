# Ekiden Architecture

Ekiden's own name is the Japanese word for a long distance relay race, and the system is built as one. No single agent covers the whole distance. Each stage hands structured output to the next, exactly like handing off a baton.

This document has three diagrams. The first shows the overall system. The second shows the main pipeline, from a user's message to a finished shortlist. The third zooms into how a single listing gets analyzed once it makes the shortlist.

## System overview

```mermaid
flowchart TB
    Browser["Browser\nNext.js static export"]
    API["FastAPI backend\nsingle Cloud Run service"]
    Orchestrator["Orchestrator\nSSE event stream"]
    Agents["Agents\npreference, area, search,\ncost, trust, eligibility, strategy"]
    Homes[["HOME'S\nlive listings"]]
    Suumo[["SUUMO\nlive listings"]]
    Fallback[("Local fallback corpus\nTokyo UR listings only")]
    Qwen[["Qwen Cloud"]]
    Aiand[["ai&"]]
    Gmi[["GMI Cloud"]]
    Gemini[["Vertex AI Gemini\nuniversal fallback"]]
    Daytona[["Daytona sandbox\ncost arithmetic"]]

    Browser <--> API
    API --> Orchestrator
    Orchestrator --> Agents
    Agents --> Homes
    Agents --> Suumo
    Agents -.Tokyo, live failed.-> Fallback
    Agents --> Qwen
    Agents --> Aiand
    Agents --> Gmi
    Agents --> Daytona
    Qwen -.unavailable.-> Gemini
    Aiand -.unavailable.-> Gemini
    Gmi -.unavailable.-> Gemini
```

The frontend and backend live in one deployed service. The browser talks directly to the API, which streams results back as they become ready rather than waiting for the whole search to finish. Every model call in every agent has Vertex AI Gemini as a safety net, so one provider being unreachable never blanks the page.

## The main pipeline

```mermaid
flowchart LR
    User(["User message"]) --> Pref["Preference agent\nextracts area, budget, layout"]
    Pref --> Area["Area resolution agent\nmaps text to a real prefecture or ward"]
    Area --> Search["Live search\nHOME'S and SUUMO, concurrently"]
    Search --> Dedup["Deduplication and filtering"]
    Dedup --> Rank["Ranking agent\npicks and orders the shortlist"]
    Rank --> Listing["Per listing analysis\nsee next diagram"]
    Listing --> Shortlist(["Shortlist shown to user"])
```

If the area or the budget is still missing after the preference agent runs, the pipeline pauses and asks a clarifying question instead of guessing. A listing that violates a stated hard constraint, such as the wrong layout or a rent over budget, can never outrank one that satisfies every constraint. That guarantee is enforced in code after ranking, not left to the model's judgment.

## Per listing analysis

```mermaid
flowchart TB
    Listing(["One shortlisted listing"])
    Cost["Cost auditor\ntrue cost from stated fees only"]
    Trust["Trust checker\nbait listing risk signals"]
    Elig["Eligibility agent\nverbatim quote grounded findings"]
    Strategy["Strategy advisor\nnegotiation and screening plan"]
    Card(["Listing card shown to user"])

    Listing --> Cost
    Listing --> Trust
    Listing --> Elig
    Cost --> Strategy
    Trust --> Strategy
    Elig --> Strategy
    Cost --> Card
    Trust --> Card
    Elig --> Card
    Strategy --> Card
```

Three of the four agents run concurrently as soon as the listing is selected. The strategy advisor runs last on purpose. It needs the real cost gaps, the real trust signals, and the specific eligibility concerns before it can give advice that is actually grounded in that listing, rather than generic tips that could apply to any apartment.

## Cost breakdown, three separate additions

The true cost figure is the part of the product most likely to be misunderstood, so it is split into three parts that are each guaranteed to add up correctly rather than shown as one opaque number.

```mermaid
flowchart TB
    subgraph Upfront["Paid once, at move in"]
        U1["First month rent and management fee"]
        U2["Security deposit"]
        U3["Key money"]
        U4["Agency fee"]
        U5["Guarantor initial fee"]
        U6["Fire insurance and key exchange"]
    end
    Upfront --> UT(["Upfront total"])

    subgraph Monthly["Ongoing monthly cost"]
        M1["Rent and management fee"]
        M2["Every upfront fee above,\nspread evenly across the lease term"]
    end
    Monthly --> MT(["Effective monthly total"])

    subgraph Renewal["After moving in, not included above"]
        R1["Guarantor company annual renewal"]
        R2["Lease renewal fee"]
    end
```

Any fee a listing does not explicitly state is excluded from every total here and disclosed separately, rather than filled in with a guessed average.

## Follow up features

```mermaid
flowchart LR
    Question(["User's free text question"]) --> FollowUp["Follow up agent"]
    FollowUp --> Answer(["Answer grounded in that listing's own data"])

    Draft(["User requests an inquiry"]) --> Email["Inquiry email agent"]
    Email --> Japanese(["Formal Japanese email"])
    Email --> Gloss(["English explanation of that email"])
```

The English text is always a gloss of the Japanese, never a substitute for it, since the Japanese body is what actually gets sent to the agency.
