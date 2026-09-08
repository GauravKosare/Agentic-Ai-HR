"""
Central config. Every value is read from environment variables (see .env.example) —
nothing is hardcoded, and nothing here should ever contain a real secret.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/backend/.env — resolved relative to this file, not the process's cwd, so it
# works the same whether you run `uvicorn app.main:app` from src/backend or run a
# script from anywhere else in the repo.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _split(csv: str) -> list[str]:
    return [m.strip() for m in csv.split(",") if m.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # --- Supabase ---
    # Using Supabase's new key format (sb_secret_.../sb_publishable_...), not the
    # legacy anon/service_role JWTs — same permissions, but each key rotates
    # independently instead of sharing one JWT signing secret. Legacy keys are
    # being deprecated by end of 2026; see src/backend/.env.example.
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_secret_key: str = Field(default="", alias="SUPABASE_SECRET_KEY")
    supabase_publishable_key: str = Field(default="", alias="SUPABASE_PUBLISHABLE_KEY")

    # --- LLM Router (TRD §3.1a) ---
    # Each *_MODELS_* value is a comma-separated CHAIN, tried in order within that
    # provider/tier: on a quota (429) error for one model, the router tries the
    # next one in the same chain before ever moving to the other provider. Only
    # once an entire chain is exhausted does it fall through — Gemini chain first,
    # then Groq's. Picked from live account quota data (Google AI Studio / Groq
    # console), 2026-07-20 — free-tier per-model limits vary by account and change
    # over time, re-verify there periodically rather than trusting this comment.
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    # Reasoning: gemini-3.5-flash and gemini-3-flash each carry a separate small
    # daily quota (~20 RPD each on a typical free account) — chaining them doubles
    # the effective daily reasoning budget on Gemini before falling to Groq.
    gemini_models_reasoning: str = Field(default="gemini-3.5-flash,gemini-3-flash", alias="GEMINI_MODELS_REASONING")
    # Light: gemini-3.1-flash-lite has the best free RPD among Gemini's actual chat
    # models (~500/day); gemma-4-26b/31b are open-weight models served through the
    # same API with a much larger daily allowance (~14.4K/day each) — a large,
    # free reserve for high-volume tasks (dedup, resume parsing) before Groq.
    gemini_models_light: str = Field(
        default="gemini-3.1-flash-lite,gemma-4-26b,gemma-4-31b", alias="GEMINI_MODELS_LIGHT"
    )

    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    # Reasoning: gpt-oss-120b is the strongest model with a full daily quota
    # (~1K RPD); llama-3.3-70b-versatile and qwen3.6-27b each add another ~1K RPD
    # once gpt-oss-120b is exhausted for the day.
    groq_models_reasoning: str = Field(
        default="openai/gpt-oss-120b,llama-3.3-70b-versatile,qwen/qwen3.6-27b", alias="GROQ_MODELS_REASONING"
    )
    # Light: gpt-oss-20b first (~1K RPD), then llama-3.1-8b-instant as a large
    # reserve (~14.4K RPD) — by far the most generous single model in either
    # provider's free tier, saved for when everything else in the chain is spent.
    groq_models_light: str = Field(
        default="openai/gpt-oss-20b,llama-3.1-8b-instant", alias="GROQ_MODELS_LIGHT"
    )

    # --- Speech-to-Text (TRD §3.7) ---
    # Groq-hosted Whisper, not self-hosted — LPU-accelerated (much lower latency
    # than CPU-only self-hosted inference), genuinely free. turbo first (faster,
    # better fit for the ~1s real-time target), large-v3 second (marginally more
    # accurate, separate quota bucket so chaining ~doubles the daily audio budget:
    # ~4,000 requests/day, ~57.6K audio-seconds/day combined, verified live
    # 2026-07-20). Shares Groq as a provider with the LLM Router fallback above —
    # see 07-Financial-Subscription-Tracking.md for the correlated-outage trade-off.
    groq_models_stt: str = Field(
        default="whisper-large-v3-turbo,whisper-large-v3", alias="GROQ_MODELS_STT"
    )

    @property
    def groq_stt_chain(self) -> list[str]:
        return _split(self.groq_models_stt)

    # --- Email (TRD §3.5) ---
    # Brevo — sole candidate messaging channel (WhatsApp deliberately excluded,
    # see 07-Financial-Subscription-Tracking.md). Permanent free tier, 300/day.
    brevo_api_key: str = Field(default="", alias="BREVO_API_KEY")
    brevo_sender_email: str = Field(default="", alias="BREVO_SENDER_EMAIL")
    brevo_sender_name: str = Field(default="AI Recruiter Agent", alias="BREVO_SENDER_NAME")

    # --- Zoom (TRD §3.6) ---
    # Server-to-Server OAuth app (not the old JWT type, which Zoom retired) —
    # marketplace.zoom.us -> Develop -> Build App -> Server-to-Server OAuth.
    # Free Basic account: unlimited 1:1 meetings, capped at 40 min/session — our
    # default interview_time_limit_minutes is 30, comfortably under that.
    zoom_account_id: str = Field(default="", alias="ZOOM_ACCOUNT_ID")
    zoom_client_id: str = Field(default="", alias="ZOOM_CLIENT_ID")
    zoom_client_secret: str = Field(default="", alias="ZOOM_CLIENT_SECRET")

    @property
    def gemini_reasoning_chain(self) -> list[str]:
        return _split(self.gemini_models_reasoning)

    @property
    def gemini_light_chain(self) -> list[str]:
        return _split(self.gemini_models_light)

    @property
    def groq_reasoning_chain(self) -> list[str]:
        return _split(self.groq_models_reasoning)

    @property
    def groq_light_chain(self) -> list[str]:
        return _split(self.groq_models_light)

    def require(self, *names: str) -> None:
        """Raise a clear error listing which env vars are missing, instead of a raw KeyError deep in a client call."""
        missing = [n for n in names if not getattr(self, n.lower(), None)]
        if missing:
            raise RuntimeError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                f"Copy .env.example to .env and fill them in."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
