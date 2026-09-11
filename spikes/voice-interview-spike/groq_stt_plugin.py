"""
Wraps the already-built app/connectors/speech_to_text.py (Groq Whisper chain) as a LiveKit
Agents STT plugin, instead of duplicating Groq key handling / chain-fallback logic here.

Verified against livekit-agents' actual plugin interface (checked 2026-09-11 via the
project's public docs/source — livekit/agents on GitHub, docs.livekit.io/reference/python):
subclasses of `stt.STT` implement `_recognize_impl(self, buffer, *, language, conn_options)
-> SpeechEvent` (see e.g. the openai plugin's stt.py, which uses the same
`rtc.combine_audio_frames(buffer).to_wav_bytes()` pattern used below). Re-check this against
whatever `livekit-agents` version actually installs if `pip install` pulls something newer —
this is a fast-moving framework.

This is non-streaming by design (STTCapabilities(streaming=False)) because Groq's Whisper
endpoint is request/response, not streaming — the spike is explicitly measuring whether that
adds too much per-turn latency for natural conversation (see docs/spikes/phase5-voice-spike.md,
"known limitations").
"""

from __future__ import annotations

from livekit import rtc
from livekit.agents import APIConnectOptions, stt
from livekit.agents.types import NOT_GIVEN, NotGivenOr

import _backend_path  # noqa: F401  (sets sys.path before the app.* import below)
from app.connectors.speech_to_text import TranscriptionUnavailable, transcribe


class GroqWhisperSTT(stt.STT):
    """Non-streaming STT plugin: buffers one utterance's frames (LiveKit's VAD-driven
    endpointing hands the whole utterance to `_recognize_impl` at once), then calls the
    existing Groq Whisper chain once per utterance.

    `language` is the spike's configured interview language (SPIKE_LANGUAGE in agent.py) —
    Groq Whisper auto-detects language from audio, but we still record which language this
    utterance was *expected* to be in, since code-switching accuracy is one of the things
    days 7-8 of the spike measure (see plan doc).
    """

    def __init__(self, language: str = "en") -> None:
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))
        self._language = language

    async def _recognize_impl(
        self,
        buffer: rtc.AudioFrame | list[rtc.AudioFrame],
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        wav_bytes = rtc.combine_audio_frames(buffer).to_wav_bytes()
        try:
            result = transcribe(wav_bytes, filename="utterance.wav")
        except TranscriptionUnavailable as exc:
            # Day 9-10 adversarial testing: surface this as a recoverable API error rather
            # than crashing the whole session mid-interview — matches how the rest of the
            # project treats a Groq-chain exhaustion (app/core/quota_guard.py's pattern).
            raise stt.APIConnectionError(f"Groq STT chain exhausted: {exc}") from exc

        resolved_language = language if language is not NOT_GIVEN else self._language
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language=resolved_language, text=result.text)],
        )
