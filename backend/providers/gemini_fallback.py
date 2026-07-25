"""Vertex AI Gemini — universal LLM fallback, tried by providers/client.py
whenever the requested primary provider (Qwen/ai&/GMI) is unconfigured or
fails even after its own retry. This sits BELOW every existing provider, not
instead of any of them, so every agent gets this fallback automatically with
zero per-agent changes.

Auth: on Cloud Run this uses the service's attached service account via
Application Default Credentials — no API key needed, just the
`roles/aiplatform.user` IAM role on that service account plus the env vars
below (GOOGLE_GENAI_USE_VERTEXAI must be exactly "true" — this is what
switches the underlying google-genai SDK from direct-Gemini-API mode to
Vertex AI mode). For local testing, run
`gcloud auth application-default login` once so the same ADC lookup finds
credentials.

Model is pinned to gemini-3.5-flash for every task tier (fast and quality
alike) — this is a fallback of last resort, not a primary tier, so one fast
model covers it.
"""
import logging
import os

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-3.5-flash"


class GeminiUnavailable(Exception):
    """Vertex AI Gemini isn't configured, or the call itself failed."""


def _use_vertexai() -> bool:
    return os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in ("true", "1", "yes")


def is_configured() -> bool:
    return _use_vertexai() and bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))


async def complete_json_gemini(system: str, user: str) -> str:
    if not is_configured():
        raise GeminiUnavailable("GOOGLE_GENAI_USE_VERTEXAI is not \"true\" or GOOGLE_CLOUD_PROJECT not set")

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise GeminiUnavailable(f"google-genai package not installed: {e}") from e

    client = genai.Client(
        vertexai=True,  # this call path only runs Vertex AI mode — see _use_vertexai() above
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
    )
    try:
        response = await client.aio.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL),
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
            ),
        )
    except Exception as e:  # noqa: BLE001 — any Vertex AI failure just means "fallback unavailable"
        raise GeminiUnavailable(f"Vertex AI Gemini call failed: {e}") from e

    if not response.text:
        raise GeminiUnavailable("Vertex AI Gemini returned an empty response")
    return response.text
