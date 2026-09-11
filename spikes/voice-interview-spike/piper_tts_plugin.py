"""
Wraps local Piper TTS inference (open source, self-hosted, no API key) as a LiveKit Agents
TTS plugin. This is the component the spike is most testing the *quality* of — Hindi/Marathi
Piper voice availability and intelligibility is an open question going in
(docs/spikes/phase5-voice-spike.md); Marathi is deliberately deferred, see README.

Verified against livekit-agents' actual plugin interface (checked 2026-09-11 via the
project's public docs/source): a non-streaming TTS implements `synthesize()` returning a
`tts.ChunkedStream` subclass whose `_run(self, output_emitter: tts.AudioEmitter)` calls
`output_emitter.initialize(...)`, `output_emitter.push(bytes)` per chunk, then
`output_emitter.flush()` — this mirrors the pattern used by the built-in elevenlabs/openai
TTS plugins, just with Piper's local synthesis instead of an HTTP call. Re-check this against
whatever `livekit-agents` version actually installs — this is a fast-moving framework.
"""

from __future__ import annotations

from pathlib import Path

from livekit.agents import APIConnectOptions, tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.utils import shortuuid
from piper import PiperVoice

PIPER_SAMPLE_RATE = 22050  # Piper's standard output rate across its released voice models.


class PiperTTS(tts.TTS):
    """`voice_path` is a path to a downloaded Piper `.onnx` model (see README step 3 —
    `python -m piper.download_voices <name> --data-dir voices/`)."""

    def __init__(self, voice_path: str | Path) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=PIPER_SAMPLE_RATE,
            num_channels=1,
        )
        voice_path = Path(voice_path)
        if not voice_path.exists():
            raise FileNotFoundError(
                f"Piper voice model not found at {voice_path}. Download it first "
                "(README step 3) — this is spike setup, not a code bug."
            )
        self._voice = PiperVoice.load(str(voice_path))

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> "_PiperChunkedStream":
        return _PiperChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class _PiperChunkedStream(tts.ChunkedStream):
    def __init__(self, *, tts: PiperTTS, input_text: str, conn_options: APIConnectOptions) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._piper_tts: PiperTTS = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        output_emitter.initialize(
            request_id=shortuuid(),
            sample_rate=PIPER_SAMPLE_RATE,
            num_channels=1,
            mime_type="audio/pcm",
        )
        # Piper's synthesize() is a synchronous generator (local ONNX inference, no network
        # I/O) — fine for a spike; if per-utterance synthesis time shows up in the latency
        # numbers days 5-6 measure, that's a real finding, not a reason to hide it behind an
        # executor here.
        for chunk in self._piper_tts._voice.synthesize(self.input_text):
            output_emitter.push(chunk.audio_int16_bytes)
        output_emitter.flush()
