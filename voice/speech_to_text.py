"""
voice/speech_to_text.py
-------------------------
Milestone 2. Records a short clip from the microphone and transcribes
it with faster-whisper (or falls back gracefully if unavailable).

Interface:
    text = SpeechToText().listen()
"""

from __future__ import annotations

from assistant.logger import get_logger

log = get_logger("voice.stt")


class SpeechToText:
    def __init__(self, model_size: str = "base", duration_seconds: float = 5.0) -> None:
        self.duration_seconds = duration_seconds
        self._model = None
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
        except Exception as e:
            log.warning(f"Speech-to-text model unavailable ({e}); voice input disabled.")
            self._model = None

    def listen(self) -> str:
        """Record audio from the default microphone and return transcribed text.
        Returns an empty string if the microphone or model is unavailable —
        callers must treat that as 'no command', not a crash."""
        if self._model is None:
            log.warning("listen() called but STT model isn't loaded.")
            return ""

        try:
            import sounddevice as sd
            import numpy as np

            sample_rate = 16000
            recording = sd.rec(
                int(self.duration_seconds * sample_rate),
                samplerate=sample_rate, channels=1, dtype="float32",
            )
            sd.wait()
            audio = np.squeeze(recording)

            segments, _ = self._model.transcribe(audio, language="en")
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        except Exception as e:
            log.error(f"Microphone/transcription failed: {e}")
            return ""
