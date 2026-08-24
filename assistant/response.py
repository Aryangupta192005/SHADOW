"""
response.py
-----------
Turns an ExecutionReport (or a clarification need) into a final
user-facing message, and speaks it if voice output is enabled.
"""

from __future__ import annotations

from assistant.executor import ExecutionReport
from assistant.logger import get_logger
from config import VOICE_ENABLED

log = get_logger("response")

_tts = None


def _get_tts():
    global _tts
    if _tts is None and VOICE_ENABLED:
        try:
            from voice.text_to_speech import TextToSpeech
            _tts = TextToSpeech()
        except Exception as e:
            log.warning(f"Voice output unavailable, falling back to text only: {e}")
            _tts = False
    return _tts or None


def say(message: str) -> None:
    print(f"SHADOW: {message}")
    tts = _get_tts()
    if tts:
        try:
            tts.speak(message)
        except Exception as e:
            log.warning(f"TTS failed: {e}")


def format_report(report: ExecutionReport) -> str:
    if report.stopped_early and not report.step_reports:
        return report.stop_reason or "I couldn't understand that request."

    lines = []
    for r in report.step_reports:
        icon = "done" if r.success else "failed"
        lines.append(f"  [{icon}] {r.tool}: {r.message}")

    if report.all_succeeded:
        header = f"Done — {report.goal}."
    elif report.stopped_early:
        header = f"Stopped — {report.stop_reason}"
    else:
        header = f"Finished with issues — {report.goal}."

    if len(lines) <= 1:
        # keep single-step responses short and conversational
        return header
    return header + "\n" + "\n".join(lines)
