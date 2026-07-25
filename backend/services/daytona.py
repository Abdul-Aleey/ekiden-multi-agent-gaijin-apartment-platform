"""Daytona sandbox execution for the Cost Auditor (BUILD_SPEC.md section 8.3).

REST shape confirmed against Daytona's public docs (daytona.io/docs), not
guessed:
  - Management API (create/delete sandbox): {DAYTONA_BASE_URL}/sandbox,
    Bearer auth. DAYTONA_BASE_URL is https://app.daytona.io/api.
  - Code execution runs against a SEPARATE fixed host, proxy.app.daytona.io
    (not configurable, not the management API host) — see
    _DAYTONA_PROXY_BASE_URL below.
  - code-run is synchronous: one POST returns the result directly, no polling.

Any failure (create/run/delete, timeout, bad response) falls back to local
computation and records that in `assumptions`, per the spec's "fail loudly,
not silently" rule — this must never be the reason a card fails to render.
"""
import json
import logging

import httpx

from config import DAYTONA_API_KEY, DAYTONA_BASE_URL

logger = logging.getLogger(__name__)

_DAYTONA_PROXY_BASE_URL = "https://proxy.app.daytona.io"
_SANDBOX_TIMEOUT_S = 20.0

LEASE_MONTHS = 24  # standard Japanese lease term, used to amortize one-time move-in fees

COST_MODEL_TEMPLATE = """
import json

def compute_cost(rent_jpy, kanrihi_jpy, shikikin_jpy, reikin_jpy, chukai_jpy,
                  hoshou_initial_jpy, kasai_hoken_jpy, kagi_koukan_jpy):
    LEASE_MONTHS = 24
    upfront_total = (rent_jpy + kanrihi_jpy + shikikin_jpy + reikin_jpy + chukai_jpy
                      + hoshou_initial_jpy + kasai_hoken_jpy + kagi_koukan_jpy)
    amortized = (round(shikikin_jpy / LEASE_MONTHS) + round(reikin_jpy / LEASE_MONTHS)
                 + round(chukai_jpy / LEASE_MONTHS) + round(hoshou_initial_jpy / LEASE_MONTHS)
                 + round(kasai_hoken_jpy / LEASE_MONTHS) + round(kagi_koukan_jpy / LEASE_MONTHS))
    effective_monthly = rent_jpy + kanrihi_jpy + amortized
    return {{
        "upfront_total_jpy": round(upfront_total),
        "effective_monthly_jpy": round(effective_monthly),
    }}

result = compute_cost({rent_jpy}, {kanrihi_jpy}, {shikikin_jpy}, {reikin_jpy},
                       {chukai_jpy}, {hoshou_initial_jpy}, {kasai_hoken_jpy}, {kagi_koukan_jpy})
print(json.dumps(result))
"""


class DaytonaUnavailable(Exception):
    pass


def _is_configured() -> bool:
    return bool(DAYTONA_API_KEY and DAYTONA_BASE_URL)


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {DAYTONA_API_KEY}", "Content-Type": "application/json"}


async def _create_sandbox(client: httpx.AsyncClient) -> str:
    resp = await client.post(f"{DAYTONA_BASE_URL.rstrip('/')}/sandbox", headers=_auth_headers(), json={})
    resp.raise_for_status()
    sandbox_id = resp.json().get("id")
    if not sandbox_id:
        raise DaytonaUnavailable(f"sandbox creation response had no 'id': {resp.text[:200]}")
    return sandbox_id


async def _run_code(client: httpx.AsyncClient, sandbox_id: str, code: str) -> dict:
    resp = await client.post(
        f"{_DAYTONA_PROXY_BASE_URL}/toolbox/{sandbox_id}/process/code-run",
        headers=_auth_headers(),
        json={"code": code, "language": "python"},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("exitCode") not in (0, None):
        raise DaytonaUnavailable(f"sandbox code exited {data.get('exitCode')}: {data.get('result')}")
    return json.loads(data["result"])


async def _delete_sandbox(client: httpx.AsyncClient, sandbox_id: str) -> None:
    try:
        await client.delete(f"{DAYTONA_BASE_URL.rstrip('/')}/sandbox/{sandbox_id}", headers=_auth_headers())
    except httpx.HTTPError as e:  # noqa: BLE001 — cleanup best-effort, never fail the caller for this
        logger.info("Daytona sandbox %s cleanup failed (non-fatal): %s", sandbox_id, e)


async def _call_sandbox(code: str) -> dict:
    if not _is_configured():
        raise DaytonaUnavailable("DAYTONA_API_KEY/DAYTONA_BASE_URL not set")
    async with httpx.AsyncClient(timeout=_SANDBOX_TIMEOUT_S) as client:
        sandbox_id = await _create_sandbox(client)
        try:
            return await _run_code(client, sandbox_id, code)
        finally:
            await _delete_sandbox(client, sandbox_id)


def compute_locally(**kwargs: int) -> dict:
    upfront_total = (
        kwargs["rent_jpy"] + kwargs["kanrihi_jpy"] + kwargs["shikikin_jpy"] + kwargs["reikin_jpy"]
        + kwargs["chukai_jpy"] + kwargs["hoshou_initial_jpy"] + kwargs["kasai_hoken_jpy"] + kwargs["kagi_koukan_jpy"]
    )
    amortized = (
        round(kwargs["shikikin_jpy"] / LEASE_MONTHS) + round(kwargs["reikin_jpy"] / LEASE_MONTHS)
        + round(kwargs["chukai_jpy"] / LEASE_MONTHS) + round(kwargs["hoshou_initial_jpy"] / LEASE_MONTHS)
        + round(kwargs["kasai_hoken_jpy"] / LEASE_MONTHS) + round(kwargs["kagi_koukan_jpy"] / LEASE_MONTHS)
    )
    return {
        "upfront_total_jpy": round(upfront_total),
        "effective_monthly_jpy": round(kwargs["rent_jpy"] + kwargs["kanrihi_jpy"] + amortized),
    }


async def run_cost_model(**kwargs: int) -> tuple[dict, bool]:
    """Returns (result_dict, ran_in_sandbox) with upfront_total_jpy and
    effective_monthly_jpy — NOT renewal fees (hoshou_annual/koushinryou), which
    agents/cost.py shows separately rather than folding into either total. Tries
    Daytona first; on any failure, computes locally and reports that via the bool."""
    if _is_configured():
        try:
            code = COST_MODEL_TEMPLATE.format(**kwargs)
            return await _call_sandbox(code), True
        except (DaytonaUnavailable, httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
            logger.warning("Daytona sandbox unavailable, computing locally: %s", e)
    return compute_locally(**kwargs), False
