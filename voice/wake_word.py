"""
voice/wake_word.py
--------------------
Milestone 7 (background mode). Placeholder for a lightweight wake-word
detector (e.g. openWakeWord / Porcupine). Not required for text mode
or push-to-talk voice mode, so it's kept as a clearly-scoped stub
rather than a half-working dependency-heavy implementation.
"""

from __future__ import annotations

from assistant.logger import get_logger
from config import WAKE_WORD

log = get_logger("voice.wake_word")


class WakeWordListener:
    def __init__(self, wake_word: str = WAKE_WORD) -> None:
        self.wake_word = wake_word

    def listen_for_wake_word(self) -> bool:
        """Blocks until the wake word is detected. Not yet implemented —
        background/always-listening mode is a later milestone."""
        log.warning("Wake-word listening is not implemented yet (Milestone 7).")
        raise NotImplementedError(
            "Wake-word mode isn't built yet. Use text mode or push-to-talk voice mode for now."
        )
