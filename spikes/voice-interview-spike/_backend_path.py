"""
Puts src/backend on sys.path so this spike can import the already-built connectors
(app.connectors.speech_to_text, app.connectors.llm_router) directly instead of duplicating
Groq/Gemini key handling and chain logic here. Import this before any `from app...` import.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2] / "src" / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
