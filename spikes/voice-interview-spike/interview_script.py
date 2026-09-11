"""
Fixed, linear interview script for days 5-10 of the spike — no adaptive follow-up logic.
Adaptive, resume-grounded interviewing is Phase 5 proper (TRD §3.7), contingent on this
spike's go/no-go. The point here is to generate enough back-and-forth turns to measure
latency and speech quality, not to interview well.
"""

from __future__ import annotations

FIXED_QUESTIONS: dict[str, list[str]] = {
    "en": [
        "Hi, thanks for joining. Could you start by telling me a bit about your background?",
        "What's a project you're proud of, and what was your role in it?",
        "How do you approach working with a tight deadline?",
        "Do you have any questions for us before we wrap up?",
    ],
    "hi": [
        "नमस्ते, जुड़ने के लिए धन्यवाद। क्या आप अपने बारे में थोड़ा बता सकते हैं?",
        "आपको अपने किस प्रोजेक्ट पर सबसे ज्यादा गर्व है?",
        "आप कम समय में काम कैसे पूरा करते हैं?",
        "क्या आपको हमसे कोई सवाल पूछना है?",
    ],
    # Marathi list left empty on purpose — fill in only once a usable Piper mr_IN voice (or
    # confirmed fallback) exists per README step 3. An empty list here is itself a spike
    # finding to record, not something to paper over with a placeholder.
    "mr": [],
}


def build_prompt(question: str, candidate_answer: str) -> str:
    """A minimal prompt for llm_router.generate(..., Task.INTERVIEW_DIALOGUE) — just enough
    to produce a natural short acknowledgement before the next fixed question, so the LLM
    Router path (not just STT/TTS) is exercised during the spike. Real interview-logic
    prompting is Phase 5 proper."""
    return (
        "You are conducting a short, friendly screening interview. "
        f"You just asked: \"{question}\"\n"
        f"The candidate answered: \"{candidate_answer}\"\n"
        "Reply with a brief (one sentence) natural acknowledgement, no new question."
    )
