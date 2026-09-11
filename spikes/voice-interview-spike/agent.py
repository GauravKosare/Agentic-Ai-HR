"""
Phase 5 voice spike — the LiveKit Agents worker.

Wires: Silero VAD -> GroqWhisperSTT -> LLM Router (Task.INTERVIEW_DIALOGUE) -> PiperTTS,
running a fixed linear interview script (interview_script.py). See
docs/spikes/phase5-voice-spike.md for the plan, day-by-day goals, and go/no-go criteria.

API verified 2026-09-11 against livekit-agents' current public docs/source (AgentServer +
@server.rtc_session(), not the older WorkerOptions/cli.run_app(WorkerOptions(...)) pattern,
which is deprecated but still works if your installed version predates this). Re-check
against whatever version `pip install -r requirements.txt` actually resolves — this framework
moves fast; don't assume this file is exact without running it once on day 1.

Run: `python agent.py dev` (after `docker compose up -d` and `pip install -r requirements.txt`).
"""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    ChatMessage,
    JobContext,
    StopResponse,
    cli,
)
from livekit.plugins import silero

import _backend_path  # noqa: F401  (sets sys.path before the app.* import below)
from app.connectors.llm_router import AIQuotaExhausted, Task, generate
from groq_stt_plugin import GroqWhisperSTT
from interview_script import FIXED_QUESTIONS, build_prompt
from piper_tts_plugin import PiperTTS

load_dotenv()
logger = logging.getLogger("voice-spike")
logger.setLevel(logging.INFO)

# Set via env or edit directly when switching which language you're testing that day —
# see docs/spikes/phase5-voice-spike.md days 7-8.
SPIKE_LANGUAGE = os.environ.get("SPIKE_LANGUAGE", "en")

_PIPER_VOICE_PATHS = {
    "en": os.environ.get("PIPER_VOICE_EN_PATH", "voices/en_US-lessac-medium.onnx"),
    "hi": os.environ.get("PIPER_VOICE_HI_PATH", "voices/hi_IN-pratham-medium.onnx"),
    "mr": os.environ.get("PIPER_VOICE_MR_PATH", ""),  # deliberately unset — see README
}


class SpikeInterviewer(Agent):
    """A fixed-script interviewer. Deliberately NOT adaptive — see interview_script.py.
    Never calls the AgentSession's own LLM node; every reply is driven manually through
    on_user_turn_completed() + StopResponse() so the LLM Router's Task.INTERVIEW_DIALOGUE
    call site is the only thing generating text, matching how the real Phase 5 agent will
    call it (TRD §3.7)."""

    def __init__(self) -> None:
        questions = FIXED_QUESTIONS.get(SPIKE_LANGUAGE, [])
        if not questions:
            raise ValueError(
                f"No fixed questions configured for language={SPIKE_LANGUAGE!r}. "
                "Record this as a spike finding (docs/spikes/phase5-voice-spike.md) rather "
                "than skipping the language silently."
            )
        voice_path = _PIPER_VOICE_PATHS.get(SPIKE_LANGUAGE, "")
        if not voice_path:
            raise ValueError(
                f"No Piper voice path configured for language={SPIKE_LANGUAGE!r} "
                f"(PIPER_VOICE_{SPIKE_LANGUAGE.upper()}_PATH). For Marathi this is expected "
                "for now — see README 'Marathi, deferred' — pick it up before days 7-8."
            )
        super().__init__(
            instructions="Fixed-script interview spike — see interview_script.py for the turns.",
            stt=GroqWhisperSTT(language=SPIKE_LANGUAGE),
            tts=PiperTTS(voice_path=voice_path),
            vad=silero.VAD.load(),
        )
        self._questions = questions
        self._index = 0

    async def on_enter(self) -> None:
        await self._ask_next()

    async def _ask_next(self) -> None:
        if self._index >= len(self._questions):
            await self.session.say("Thanks, that's all the questions I have. Goodbye for now.")
            return
        question = self._questions[self._index]
        self._index += 1
        await self.session.say(question)

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Called once STT commits a final transcript for the user's turn. Measures turn
        latency, calls the LLM Router for a one-line acknowledgement, speaks it, then asks
        the next fixed question — and raises StopResponse() so the session's own default
        LLM node never also fires (we're driving replies manually here, on purpose)."""
        turn_started_at = time.monotonic()
        candidate_answer = new_message.text_content or ""

        try:
            result = generate(
                build_prompt(self._questions[self._index - 1], candidate_answer),
                Task.INTERVIEW_DIALOGUE,
            )
            ack_text = result.text
        except AIQuotaExhausted as exc:
            # Same pause-and-notify contract as the rest of the app (app/core/quota_guard.py) —
            # for the spike, just log it and skip straight to the next fixed question rather
            # than wiring the full Owner-notification flow into a disposable prototype.
            logger.warning("AIQuotaExhausted mid-spike: %s", exc)
            ack_text = "Thank you."

        latency_s = time.monotonic() - turn_started_at
        logger.info(
            "[SPIKE] turn latency=%.2fs lang=%s answer=%r ack=%r",
            latency_s, SPIKE_LANGUAGE, candidate_answer, ack_text,
        )

        await self.session.say(ack_text)
        await self._ask_next()
        raise StopResponse()


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name, "spike_language": SPIKE_LANGUAGE}
    session = AgentSession()
    await session.start(agent=SpikeInterviewer(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
