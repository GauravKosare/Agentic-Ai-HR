"""
Wraps local Piper TTS inference (open source, self-hosted, no API key) as a LiveKit Agents
TTS plugin. This is the component the spike is most testing the *quality* of — Hindi/Marathi
Piper voice availability and intelligibility is an open question going in
(docs/spikes/phase5-voice-spike.md).

NOTE — verify against the current LiveKit Agents plugin interface before day 1, same caveat
as groq_stt_plugin.py: base-class method names shift as the framework evolves.
"""

from __future__ import annotations

import os

from livekit.agents import tts
from piper import PiperVoice

# One PiperVoice per language, loaded once at process start (model load is the slow part;
# per-utterance synthesis is fast). Empty string for a language means "no voice available for
# it yet" — a real spike finding for Marathi if PIPER_VOICE_MR is unset, not a silent skip.
_VOICE_PATHS = {
    "en": os.environ.get("PIPER_VOICE_EN", "en_US-lessac-medium"),
    "hi": os.environ.get("PIPER_VOICE_HI", "hi_IN-pratham-medium"),
    "mr": os.environ.get("PIPER_VOICE_MR", ""),
}


class PiperTTS(tts.TTS):
    def __init__(self, language: str = "en") -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=22050,
            num_channels=1,
        )
        voice_path = _VOICE_PATHS.get(language)
        if not voice_path:
            raise ValueError(
                f"No Piper voice configured for language={language!r}. "
                "This is a spike finding, not a bug — log it in the go/no-go writeup "
                "(docs/spikes/phase5-voice-spike.md) rather than silently falling back."
            )
        self._voice = PiperVoice.load(voice_path)

    def synthesize(self, text: str) -> tts.ChunkedStream:
        audio_bytes = b"".join(chunk.audio_int16_bytes for chunk in self._voice.synthesize(text))
        return tts.ChunkedStream(audio_data=audio_bytes, sample_rate=22050, num_channels=1)
