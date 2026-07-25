import os
from dataclasses import dataclass, field
from typing import Optional


class ProviderNotConfigured(Exception):
    """Raised when an agent tries to call a provider whose env vars aren't set yet.

    Callers catch this and degrade gracefully (see agents/*.py), never crash the request.
    """


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: Optional[str]
    api_key: Optional[str]
    model: Optional[str]
    extra_body: dict = field(default_factory=dict)

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def require(self) -> "Provider":
        if not self.is_configured:
            raise ProviderNotConfigured(
                f"Provider '{self.name}' is missing base_url/api_key/model env vars."
            )
        return self


def _provider(
    name: str, base_url_var: str, api_key_var: str, model_var: str, extra_body: dict | None = None
) -> Provider:
    return Provider(
        name=name,
        base_url=os.environ.get(base_url_var),
        api_key=os.environ.get(api_key_var),
        model=os.environ.get(model_var),
        extra_body=extra_body or {},
    )


# Real sponsor accounts, one model each, per task:
#   - "qwen": genuine Qwen Cloud (dashscope-intl, OpenAI-compatible mode) —
#     qwen3.5-flash. Handles the high-volume, low-complexity tasks (preference
#     extraction, area resolution, search ranking, fee extraction, translation,
#     follow-up Q&A). enable_thinking is forced off in extra_body — leaving
#     Qwen's default thinking mode on reproduced the exact multi-minute
#     chain-of-thought latency problem seen with a reasoning model in Round 5
#     (see MEMORY.md), which is unacceptable for a call made many times per
#     search.
#   - "aiand_fast" / "aiand_quality": ai& account (AIAND_BASE_URL/AIAND_API_KEY),
#     two model tiers. "aiand_fast" is now only trust.py's fallback tier before
#     GMI reaches rule-based (kept as a distinct vendor from Qwen so that
#     fallback isn't the same model doing ranking too). "aiand_quality" still
#     does eligibility analysis and the inquiry email — both carry sensitive
#     visa/income data, routed through the Japan-hosted provider.
#   - "gmi": GMI Cloud — independent vendor for the trust/bait-listing check,
#     deliberately not Qwen or ai& so it's a genuine second opinion.
# Built lazily so dev/test doesn't need every key set.
def get_registry() -> dict[str, Provider]:
    return {
        "qwen": _provider(
            "qwen", "QWEN_BASE_URL", "QWEN_API_KEY", "QWEN_MODEL", extra_body={"enable_thinking": False}
        ),
        "aiand_fast": _provider("aiand_fast", "AIAND_BASE_URL", "AIAND_API_KEY", "AIAND_MODEL_FAST"),
        "aiand_quality": _provider("aiand_quality", "AIAND_BASE_URL", "AIAND_API_KEY", "AIAND_MODEL_QUALITY"),
        "gmi": _provider("gmi", "GMI_BASE_URL", "GMI_API_KEY", "GMI_MODEL"),
    }
