import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from agents.followup import answer_followup
from agents.inquiry import write_inquiry
from config import ALLOWED_ORIGINS
from orchestrator import run_chat_turn
from schemas import ChatTurnRequest, FollowupRequest, InquiryRequest, ListingCard
from services.provider_status import check_all_providers

logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d %(levelname)s:%(name)s:%(message)s", datefmt="%H:%M:%S")

app = FastAPI(title="Ekiden API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory only, per BUILD_SPEC.md section 2 ("no DB, nothing persists").
# Holds the most recent shortlist's ListingCards so /followup and /inquiry
# can reference a listing without re-running search.
_session_cards: dict[str, ListingCard] = {}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def status():
    """Live reachability per sponsor provider, for the NavBar status pills.
    One of: "ok" (reachable, real call succeeded), "error" (configured but
    unreachable/failing), "not_configured" (no env vars set),
    "configured_untested" (Daytona — env vars present but no ping implemented
    yet, see services/daytona.py)."""
    return await check_all_providers()


@app.post("/api/chat")
async def chat(req: ChatTurnRequest):
    async def event_stream():
        async for event_name, data in run_chat_turn(req.message, req.profile, req.prior_prefs, lang=req.lang):
            if event_name == "card":
                card = ListingCard(**data)
                _session_cards[card.listing.id] = card
            yield {"event": event_name, "data": json.dumps(data, ensure_ascii=False, default=str)}

    return EventSourceResponse(event_stream())


@app.post("/api/listing/{listing_id}/followup")
async def followup(listing_id: str, req: FollowupRequest):
    card = _session_cards.get(listing_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Listing not found in current session shortlist")
    answer = await answer_followup(card, req.question, req.lang)
    return {"answer": answer}


@app.post("/api/listing/{listing_id}/inquiry")
async def inquiry(listing_id: str, req: InquiryRequest):
    card = _session_cards.get(listing_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Listing not found in current session shortlist")
    email = await write_inquiry(card.listing, req.profile, card.eligibility)
    return email.model_dump()


# Single-Cloud-Run-service deploy shape: the frontend is built as a Next.js
# static export (frontend/next.config.mjs `output: "export"`) and served
# directly by this same FastAPI app, same origin as /api/* — no separate
# frontend service, no CORS in production. Mounted LAST so it never shadows
# the API routes above. Only present if the export actually exists (absent
# in local dev, where the frontend normally runs via `next dev` on :3000
# instead), so this never breaks local backend-only runs.
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "out"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
