"""
Wraps the already-built app/connectors/speech_to_text.py (Groq Whisper chain) as a LiveKit
Agents STT plugin, instead of duplicating Groq key handling / chain-fallback logic here.

NOTE — verify against the current LiveKit Agents plugin interface before day 1: the exact
base-class method signature (`_recognize_impl` vs. whatever the installed livekit-agents
version calls it) moves as the framework evolves. This targets the non-streaming
"recognize a whole utterance" shape, which matches how transcribe() already works — Groq's
Whisper endpoint is request/response, not streaming, which is itself one of the things this
spike is measuring (see docs/spikes/phase5-voice-spike.md, "known limitations").
"""

from __future__ import annotations

import io
import wave

import _backend_path  # noqa: F401  (sets sys.path before the app.* import below)
from livekit import rtc
from livekit.agents import stt

from app.connectors.speech_to_text import TranscriptionUnavailable, transcribe


def _frames_to_wav_bytes(frames: list[rtc.AudioFrame]) -> bytes:
    """Concatenate buffered AudioFrames (as VAD hands them over between speech
    start/end) into a single mono WAV blob for transcribe()."""
    if not frames:
        return b""
    sample_rate = frames[0].sample_rate
    num_channels = frames[0].num_channels
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(2)  # 16-bit PCM, matches LiveKit's default frame format
        wav_file.setframerate(sample_rate)
        for frame in frames:
            wav_file.writeframes(bytes(frame.data))
    return buffer.getvalue()


class GroqWhisperSTT(stt.STT):
    """Non-streaming STT plugin: buffers one utterance's frames, then calls the
    existing Groq Whisper chain once per utterance."""

    def __init__(self) -> None:
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))

    async def _recognize_impl(self, buffer: list[rtc.AudioFrame], *, language: str | None = None, **kwargs) -> stt.SpeechEvent:
        wav_bytes = _frames_to_wav_bytes(buffer)
        try:
            result = transcribe(wav_bytes, filename="utterance.wav")
        except TranscriptionUnavailable as exc:
            # Day 9-10 adversarial testing: log this, don't crash the agent mid-interview.
            raise stt.APIConnectionError(f"Groq STT chain exhausted: {exc}") from exc

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=result.text, language=language or "")],
        )
