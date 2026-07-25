import json
import logging
import re

import httpx

from providers.gemini_fallback import GeminiUnavailable, complete_json_gemini
from providers.registry import ProviderNotConfigured, get_registry

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class AgentError(Exception):
    """Raised when a provider call fails twice in a row AND the Vertex AI
    Gemini fallback (providers/gemini_fallback.py) also can't serve the
    request. Orchestrator catches this per-agent and renders a partial
    result instead of blanking the page."""


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


def _parse_json_lenient(text: str) -> dict:
    """Some models (observed on the ai&-hosted endpoint) prepend an
    extra stray '{' before an otherwise well-formed JSON object. Try the
    literal text first; if that fails and it looks like this specific glitch
    (starts with '{{' but the brace count is unbalanced by exactly one),
    retry with one leading brace stripped before giving up."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if text.startswith("{{") and text.count("{") - text.count("}") == 1:
            return json.loads(text[1:])
        raise


async def _call_once(provider_name: str, system: str, user: str) -> str:
    provider = get_registry()[provider_name].require()
    # Generous timeout: some hosted models (observed on this ai&-hosted
    # endpoint) emit verbose chain-of-thought reasoning tokens before the
    # final answer, which can take well over 30s on a large prompt (e.g. a
    # 30-candidate ranking call).
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            f"{provider.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": provider.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                **provider.extra_body,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _complete_json_primary(provider: str, system: str, user: str, schema_hint: str) -> dict:
    """The original single-provider path — unchanged behavior, just renamed
    so complete_json (below) can wrap it with the Vertex AI Gemini fallback."""
    full_user = f"{user}\n\nRespond with JSON matching this shape:\n{schema_hint}"

    try:
        raw = await _call_once(provider, system, full_user)
        return _parse_json_lenient(_strip_fences(raw))
    except json.JSONDecodeError as first_error:
        retry_user = (
            f"{full_user}\n\nYour previous response failed to parse as JSON "
            f"({first_error}). Return ONLY valid JSON, no prose, no markdown fences."
        )
        raw = await _call_once(provider, system, retry_user)
        return _parse_json_lenient(_strip_fences(raw))
    except httpx.HTTPError as e:
        raise AgentError(f"{provider} request failed: {e}") from e


async def complete_json(provider: str, system: str, user: str, schema_hint: str) -> dict:
    """Call `provider`'s /chat/completions, forcing JSON output.

    Strips ```json fences before parsing, retries once on a parse error. If
    `provider` is unconfigured or still fails after that retry, falls back to
    Vertex AI Gemini (providers/gemini_fallback.py) as one more real-model
    attempt before giving up — this applies at every call site automatically,
    not per-agent. Raises AgentError only if BOTH the requested provider and
    the Gemini fallback fail.
    """
    try:
        return await _complete_json_primary(provider, system, user, schema_hint)
    except (AgentError, ProviderNotConfigured, json.JSONDecodeError, httpx.HTTPError) as primary_error:
        logger.info("provider '%s' unavailable (%s), trying Vertex AI Gemini fallback", provider, primary_error)
        try:
            full_user = f"{user}\n\nRespond with JSON matching this shape:\n{schema_hint}"
            raw = await complete_json_gemini(system, full_user)
            return _parse_json_lenient(_strip_fences(raw))
        except (GeminiUnavailable, json.JSONDecodeError) as gemini_error:
            raise AgentError(
                f"'{provider}' failed ({primary_error}) and Vertex AI Gemini fallback also "
                f"unavailable ({gemini_error})"
            ) from primary_error
