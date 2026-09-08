"""
Run this after filling in .env to confirm each connector can actually reach its
service. Never prints secret values — only pass/fail and the provider's own error
message (which SDKs generally keep free of the key itself).

Usage (from src/backend):
    python -m scripts.check_connectors
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.connectors import email, llm_router, speech_to_text, supabase_client, zoom  # noqa: E402


def main() -> int:
    checks = [
        ("Supabase", supabase_client.health_check),
        ("LLM Router (Gemini -> Groq)", llm_router.health_check),
        ("Speech-to-Text (Groq Whisper)", speech_to_text.health_check),
        ("Email (Brevo)", email.health_check),
        ("Zoom", zoom.health_check),
    ]

    all_ok = True
    print("Checking connectors...\n")
    for name, check_fn in checks:
        ok, detail = check_fn()
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")
        all_ok = all_ok and ok

    print()
    if all_ok:
        print("All connectors healthy.")
    else:
        print("One or more connectors failed. Check the .env values against .env.example.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
