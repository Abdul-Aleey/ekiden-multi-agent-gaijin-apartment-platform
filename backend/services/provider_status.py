"""Lightweight live reachability check for each sponsor provider, used by
GET /api/status to drive the NavBar's live/dead indicator pills. Deliberately
separate from providers/client.py's complete_json (which is tuned for real
agent calls with JSON-forcing and retries) — this uses a short timeout and
minimal prompt since it's just a health signal, not real work, and some
configured models (e.g. reasoning models with verbose chain-of-thought) are
too slow for a per-page-load check at their normal call shape.
"""
import asyncio

import httpx

from providers.gemini_fallback import complete_json_gemini, is_configured as gemini_is_configured
from providers.registry import get_registry

_PING_TIMEOUT_S = 10.0


async def _ping_llm_provider(name: str) -> str:
    provider = get_registry()[name]
    if not provider.is_configured:
        return "not_configured"
    try:
        async with httpx.AsyncClient(timeout=_PING_TIMEOUT_S) as client:
            resp = await client.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"},
                json={
                    "model": provider.model,
                    "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
                    "max_tokens": 5,
                    **provider.extra_body,
                },
            )
            resp.raise_for_status()
            return "ok"
    except Exception:  # noqa: BLE001 — any failure means "can't reach it", that's the signal
        return "error"


async def _daytona_status() -> str:
    from config import DAYTONA_API_KEY, DAYTONA_BASE_URL

    if not (DAYTONA_API_KEY and DAYTONA_BASE_URL):
        return "not_configured"
    try:
        async with httpx.AsyncClient(timeout=_PING_TIMEOUT_S) as client:
            resp = await client.get(
                f"{DAYTONA_BASE_URL.rstrip('/')}/sandbox",
                headers={"Authorization": f"Bearer {DAYTONA_API_KEY}"},
            )
            resp.raise_for_status()
            return "ok"
    except Exception:  # noqa: BLE001 — any failure means "can't reach it", that's the signal
        return "error"


async def _gemini_status() -> str:
    if not gemini_is_configured():
        return "not_configured"
    try:
        async with asyncio.timeout(_PING_TIMEOUT_S):
            await complete_json_gemini("Reply with JSON.", 'Reply with {"ok": true}')
        return "ok"
    except Exception:  # noqa: BLE001 — any failure means "can't reach it", that's the signal
        return "error"


async def check_all_providers() -> dict[str, str]:
    qwen, aiand_fast, aiand_quality, gmi, daytona, gemini = await asyncio.gather(
        _ping_llm_provider("qwen"),
        _ping_llm_provider("aiand_fast"),
        _ping_llm_provider("aiand_quality"),
        _ping_llm_provider("gmi"),
        _daytona_status(),
        _gemini_status(),
    )
    return {
        "qwen": qwen,
        "aiand_fast": aiand_fast,
        "aiand_quality": aiand_quality,
        "gmi": gmi,
        "daytona": daytona,
        "gemini": gemini,
    }
