"""
Speech-to-Text connector — TRD §3.7.

Uses Groq's hosted Whisper (whisper-large-v3-turbo, whisper-large-v3) instead of
self-hosting Whisper on the Oracle Cloud VM — LPU-accelerated, genuinely free,
and directly addresses the latency risk documented against CPU-only self-hosted
inference (07-Financial-Subscription-Tracking.md §4a).

Same chain pattern as the LLM Router (llm_router.py): try whisper-large-v3-turbo
first (faster — better fit for the interview's ~1s real-time round-trip target);
on a quota (429) error, fall back to whisper-large-v3 (marginally more accurate,
separate quota bucket, so this roughly doubles the daily audio budget rather than
just being a slower retry of the same limit).

Shared-provider risk: this and llm_router.py both call Groq. A Groq-wide outage
or account issue affects both the LLM fallback path and this STT path at the same
time — that's a correlated failure, not two independent ones. There is currently
no second STT provider to fall back to if Groq's entire chain is exhausted or
down; TranscriptionUnavailable surfaces that distinctly so the caller can decide
how to degrade (e.g. reschedule the interview) rather than crashing on a raw
exception.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.connectors._shared import try_chain
from app.core.config import get_settings


@dataclass
class STTResult:
    text: str
    provider: str  # "groq"
    model: str


class TranscriptionUnavailable(Exception):
    """
    Raised when every model in the Groq STT chain is exhausted or erroring on
    quota grounds. Unlike AIQuotaExhausted (llm_router.py) there's no second
    provider to fall through to here — the caller decides how to handle a live
    interview losing STT mid-call (TRD §8 failure handling).
    """

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Groq STT chain exhausted. {detail}")


def _call_groq_stt(model: str, audio_bytes: bytes, filename: str) -> STTResult:
    from groq import Groq

    settings = get_settings()
    settings.require("groq_api_key")
    client = Groq(api_key=settings.groq_api_key)
    transcription = client.audio.transcriptions.create(
        model=model,
        file=(filename, audio_bytes),
    )
    return STTResult(text=transcription.text, provider="groq", model=model)


def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> STTResult:
    """
    The single entry point the Meeting Bot / Live Interview Agent (TRD §3.7)
    should call for STT. `audio_bytes` is a short utterance/chunk, not a whole
    interview — matches how the real-time pipeline streams audio in.
    """
    settings = get_settings()
    result, errors = try_chain(
        settings.groq_stt_chain,
        lambda model: _call_groq_stt(model, audio_bytes, filename),
    )
    if result is not None:
        return result
    raise TranscriptionUnavailable("; ".join(errors))


def _silent_wav_bytes(seconds: float = 0.5) -> bytes:
    """A tiny synthetic silent WAV, generated in-memory with the stdlib — no test
    fixture file needed just to confirm the API is reachable and the key is valid."""
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buffer.getvalue()


def health_check() -> tuple[bool, str]:
    """Cheap connectivity check — transcribes half a second of silence, no real cost against the free tier."""
    try:
        result = transcribe(_silent_wav_bytes(), filename="health_check.wav")
        return True, f"OK via {result.provider} ({result.model})"
    except TranscriptionUnavailable as exc:
        return False, f"Every free-tier STT model is exhausted right now. {exc.detail}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Speech-to-Text health check failed: {exc}"
