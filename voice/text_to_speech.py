"""
voice/text_to_speech.py
------------------------
Milestone 2. Thin wrapper around pyttsx3 (offline TTS). Kept isolated
so it can be swapped for edge-tts or another engine later without
touching assistant/response.py.
"""

from __future__ import annotations

from assistant.logger import get_logger

log = get_logger("voice.tts")


class TextToSpeech:
    def __init__(self) -> None:
        self._engine = None
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
        except Exception as e:
            log.warning(f"pyttsx3 unavailable ({e}); TTS will no-op.")
            self._engine = None

    def speak(self, text: str) -> None:
        if not text:
            return
        if self._engine is None:
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            log.warning(f"TTS speak failed: {e}")
