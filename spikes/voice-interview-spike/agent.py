"""
Phase 5 voice spike — the LiveKit Agents worker.

Wires: Silero VAD -> GroqWhisperSTT -> LLM Router (Task.INTERVIEW_DIALOGUE) -> PiperTTS,
running a fixed linear interview script (interview_script.py). See
docs/spikes/phase5-voice-spike.md for the plan, day-by-day goals, and go/no-go criteria.

NOTE: LiveKit's Agents framework API surface moves quickly. This targets the ~1.0
`AgentSession` / `Agent` shape current as of early 2026 (the assistant's knowledge cutoff) —
before day 1, confirm the installed `livekit-agents` version's actual API against
https://docs.livekit.io/agents/ and adjust the wiring below rather than assuming this is
exact. That reconciliation is expected spike setup work, not a sign something here is wrong.

Run: `python agent.py dev` (after `docker compose up -d` and `pip install -r requirements.txt`).
"""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
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


class SpikeInterviewer(Agent):
    """A fixed-script interviewer. Deliberately NOT adaptive — see interview_script.py."""

    def __init__(self) -> None:
        questions = FIXED_QUESTIONS.get(SPIKE_LANGUAGE, [])
        if not questions:
            raise ValueError(
                f"No fixed questions configured for language={SPIKE_LANGUAGE!r}. "
                "Record this as a spike finding (docs/spikes/phase5-voice-spike.md) rather "
                "than skipping the language silently."
            )
        super().__init__(
            instructions="Fixed-script interview spike — see interview_script.py for the turns.",
            stt=GroqWhisperSTT(),
            tts=PiperTTS(language=SPIKE_LANGUAGE),
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

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """Called once STT finishes an utterance. Measures turn latency and calls the LLM
        Router for a one-line acknowledgement before moving to the next fixed question —
        exercising the same AIQuotaExhausted path already handled elsewhere in the project,
        not a new failure mode invented for the spike."""
        turn_started_at = time.monotonic()
        candidate_answer = new_message.text_content

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
        logger.info("[SPIKE] turn latency=%.2fs lang=%s answer=%r ack=%r", latency_s, SPIKE_LANGUAGE, candidate_answer, ack_text)

        await self.session.say(ack_text)
        await self._ask_next()


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    session = AgentSession()
    await session.start(agent=SpikeInterviewer(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
