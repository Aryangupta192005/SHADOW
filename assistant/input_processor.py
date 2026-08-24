"""
input_processor.py
-------------------
Normalizes input from either the keyboard or the microphone into a
single plain-text command, so the rest of the app never needs to
know which mode produced it.
"""

from __future__ import annotations

from assistant.logger import get_logger
from config import VOICE_ENABLED

log = get_logger("input_processor")

_stt = None


def _get_stt():
    global _stt
    if _stt is None:
        try:
            from voice.speech_to_text import SpeechToText
            _stt = SpeechToText()
        except Exception as e:
            log.warning(f"Voice input unavailable: {e}")
            _stt = False
    return _stt or None


def get_command(mode: str = "text") -> str:
    """Return a normalized command string.

    mode="text"  -> reads a line from stdin
    mode="voice" -> records + transcribes from the microphone
    """
    if mode == "voice":
        if not VOICE_ENABLED:
            log.warning("Voice mode requested but VOICE_ENABLED=false in config; falling back to text.")
            return input("You: ").strip()
        stt = _get_stt()
        if stt is None:
            print("(voice input unavailable — falling back to text)")
            return input("You: ").strip()
        print("Listening...")
        text = stt.listen()
        if not text:
            print("(didn't catch that)")
        else:
            print(f"You (voice): {text}")
        return text

    return input("You: ").strip()
