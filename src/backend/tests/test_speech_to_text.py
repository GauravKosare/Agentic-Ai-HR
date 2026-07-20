"""
Unit tests for the parts of the Speech-to-Text connector that don't need real
network calls. The real Groq Whisper call is exercised by
scripts/check_connectors.py against real credentials.
"""

import wave

from app.connectors.speech_to_text import _silent_wav_bytes


def test_silent_wav_bytes_is_a_valid_wav_file():
    import io

    audio = _silent_wav_bytes(seconds=0.5)
    with wave.open(io.BytesIO(audio), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 16000
        # 0.5s at 16kHz mono, 16-bit — roughly half a second of frames
        assert wav_file.getnframes() == 8000
