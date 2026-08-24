"""
ui/interface.py
-----------------
SHADOW's desktop GUI.
"""

from __future__ import annotations

import threading
from pathlib import Path

from assistant import memory
from assistant.brain import understand
from assistant.executor import execute_plan
from assistant.logger import get_logger
from assistant.planner import build_plan
from assistant.response import format_report
from config import ASSISTANT_NAME, VOICE_ENABLED

log = get_logger("ui")

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.jpg"


def launch_gui() -> None:
    try:
        from PySide6.QtCore import Qt, QObject, Signal, Slot
        from PySide6.QtGui import QShortcut, QKeySequence, QIcon
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox,
        )
    except ImportError:
        raise RuntimeError(
            "The desktop GUI needs PySide6. Install it with:\n"
            "    pip install PySide6\n"
            "(it's already listed, commented out, in requirements.txt)"
        )

    class ConfirmBridge(QObject):
        """Carries a confirmation request from the worker thread to the
        GUI thread, and the user's answer back again."""
        requested = Signal(str, object)  # prompt, (result_dict, threading.Event)

    class ResultBridge(QObject):
        message_ready = Signal(str, str)   # who, text
        status_changed = Signal(str)
        finished = Signal()

    class CommandWorker(threading.Thread):
        """Runs one command through the full SHADOW pipeline off the GUI thread."""

        def __init__(self, text: str, bridge: ResultBridge, confirm_bridge: ConfirmBridge, stop_event: threading.Event):
            super().__init__(daemon=True)
            self.text = text
            self.bridge = bridge
            self.confirm_bridge = confirm_bridge
            self.stop_event = stop_event

        def _confirm(self, prompt: str) -> bool:
            result: dict = {}
            done = threading.Event()
            self.confirm_bridge.requested.emit(prompt, (result, done))
            done.wait()
            return result.get("approved", False)

        def run(self):
            self.bridge.status_changed.emit("Thinking...")
            intent = understand(self.text)
            plan = build_plan(intent)

            if not plan.valid:
                self.bridge.message_ready.emit("SHADOW", plan.error or "I couldn't figure that out.")
                self.bridge.status_changed.emit("Idle")
                self.bridge.finished.emit()
                return

            self.bridge.status_changed.emit("Working...")
            report = execute_plan(plan, confirm_callback=self._confirm, stop_event=self.stop_event)
            self.bridge.message_ready.emit("SHADOW", format_report(report))
            memory.record_task(goal=report.goal, success=report.all_succeeded,
                                summary=report.stop_reason or "")
            self.bridge.status_changed.emit("Idle")
            self.bridge.finished.emit()

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle(ASSISTANT_NAME)
            self.resize(480, 640)
            if LOGO_PATH.exists():
                self.setWindowIcon(QIcon(str(LOGO_PATH)))

            self.stop_event = threading.Event()
            self.worker: CommandWorker | None = None

            self.bridge = ResultBridge()
            self.bridge.message_ready.connect(self._on_message)
            self.bridge.status_changed.connect(self._on_status)
            self.bridge.finished.connect(self._on_finished)

            self.confirm_bridge = ConfirmBridge()
            self.confirm_bridge.requested.connect(self._on_confirm_requested, Qt.QueuedConnection)

            root = QWidget()
            layout = QVBoxLayout(root)

            title = QLabel(ASSISTANT_NAME)
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
            layout.addWidget(title)

            self.status_label = QLabel("● Idle")
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setStyleSheet("color: gray; padding-bottom: 6px;")
            layout.addWidget(self.status_label)

            self.history = QTextEdit()
            self.history.setReadOnly(True)
            layout.addWidget(self.history, stretch=1)

            input_row = QHBoxLayout()
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("Type your request…")
            self.input_field.returnPressed.connect(self._on_send)
            input_row.addWidget(self.input_field, stretch=1)

            self.send_button = QPushButton("Send")
            self.send_button.clicked.connect(self._on_send)
            input_row.addWidget(self.send_button)

            self.mic_button = QPushButton("🎤")
            self.mic_button.setFixedWidth(40)
            self.mic_button.setEnabled(VOICE_ENABLED)
            self.mic_button.setToolTip(
                "Voice input" if VOICE_ENABLED else
                "Voice input isn't enabled yet — set VOICE_ENABLED=true in .env (Milestone 2)."
            )
            self.mic_button.clicked.connect(self._on_mic)
            input_row.addWidget(self.mic_button)

            layout.addLayout(input_row)

            self.stop_button = QPushButton("STOP")
            self.stop_button.setStyleSheet(
                "background-color: #b00020; color: white; font-weight: bold; padding: 6px;"
            )
            self.stop_button.clicked.connect(self._on_stop)
            layout.addWidget(self.stop_button)

            self.setCentralWidget(root)

            QShortcut(QKeySequence("Esc"), self, activated=self._on_stop)

            self._append_history("SHADOW", f"{ASSISTANT_NAME} is ready. What do you need?")

        def _on_send(self):
            text = self.input_field.text().strip()
            if not text:
                return
            if self.worker is not None and self.worker.is_alive():
                self._append_history("SHADOW", "Still working on the last request — use STOP if you want to cancel it.")
                return

            self._append_history("You", text)
            self.input_field.clear()
            self.stop_event.clear()
            self.worker = CommandWorker(text, self.bridge, self.confirm_bridge, self.stop_event)
            self.worker.start()

        def _on_mic(self):
            if not VOICE_ENABLED:
                return
            try:
                from voice.speech_to_text import SpeechToText
                self._on_status("Listening...")
                text = SpeechToText().listen()
                self._on_status("Idle")
                if text:
                    self.input_field.setText(text)
                    self._on_send()
                else:
                    self._append_history("SHADOW", "(didn't catch that)")
            except Exception as e:
                log.warning(f"Voice input failed: {e}")
                self._append_history("SHADOW", "Voice input isn't available right now.")

        def _on_stop(self):
            if self.worker is not None and self.worker.is_alive():
                self.stop_event.set()
                self._append_history("SHADOW", "Stopping after the current step…")
            self._on_status("Idle")

        @Slot(str, str)
        def _on_message(self, who: str, text: str):
            self._append_history(who, text)

        @Slot(str)
        def _on_status(self, text: str):
            self.status_label.setText(f"● {text}")
            color = {"Idle": "gray", "Listening...": "#1a73e8"}.get(text, "#b8860b")
            self.status_label.setStyleSheet(f"color: {color}; padding-bottom: 6px;")

        @Slot()
        def _on_finished(self):
            self.worker = None

        @Slot(str, object)
        def _on_confirm_requested(self, prompt: str, payload):
            result, done = payload
            answer = QMessageBox.question(
                self, "Confirm action", prompt,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            result["approved"] = answer == QMessageBox.Yes
            done.set()

        def _append_history(self, who: str, text: str):
            self.history.append(f"<b>{who}:</b> {text}")

        def closeEvent(self, event):
            self.stop_event.set()
            event.accept()

    memory.init_db()
    app = QApplication.instance() or QApplication([])
    if LOGO_PATH.exists():
        app.setWindowIcon(QIcon(str(LOGO_PATH)))
    window = MainWindow()
    window.show()
    app.exec()