"""
main.py
-------
SHADOW entry point.

Milestone 1: a working text assistant.
    UNDERSTAND -> PLAN -> SAFETY CHECK -> ACT -> OBSERVE -> RESPOND

Run:
    python main.py            # text mode
    python main.py --voice    # voice input (requires Milestone 2 deps + VOICE_ENABLED=true)
"""

from __future__ import annotations

import argparse
import sys

from assistant import memory
from assistant.brain import understand
from assistant.executor import execute_plan
from assistant.input_processor import get_command
from assistant.logger import get_logger
from assistant.planner import build_plan
from assistant.response import format_report, say
from config import ASSISTANT_NAME

log = get_logger("main")

EXIT_WORDS = {"exit", "quit", "stop", "goodbye", "bye"}


def confirm_via_console(prompt: str) -> bool:
    answer = input(f"\n[CONFIRM] {prompt} (yes/no): ").strip().lower()
    return answer in ("y", "yes")


def handle_command(text: str) -> None:
    intent = understand(text)
    plan = build_plan(intent)

    if not plan.valid:
        say(plan.error or "I couldn't figure out what to do with that.")
        return

    report = execute_plan(plan, confirm_callback=confirm_via_console)
    say(format_report(report))
    memory.record_task(goal=report.goal, success=report.all_succeeded,
                        summary=report.stop_reason or "")


def run_text_loop() -> None:
    print(f"{ASSISTANT_NAME} is ready. Type your request, or 'exit' to quit.\n")
    while True:
        try:
            text = get_command(mode="text")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.strip().lower() in EXIT_WORDS:
            say("Goodbye.")
            break

        handle_command(text)


def run_voice_loop() -> None:
    print(f"{ASSISTANT_NAME} is ready in voice mode. Say 'stop' to quit.\n")
    while True:
        try:
            text = get_command(mode="voice")
        except KeyboardInterrupt:
            print()
            break

        if not text:
            continue
        if text.strip().lower() in EXIT_WORDS:
            say("Goodbye.")
            break

        handle_command(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ASSISTANT_NAME} — personal AI desktop assistant")
    parser.add_argument("--voice", action="store_true", help="Run in voice input mode instead of text mode.")
    parser.add_argument("--gui", action="store_true", help="Launch the desktop GUI instead of the console.")
    args = parser.parse_args()

    if args.gui:
        log.info(f"{ASSISTANT_NAME} starting (gui)")
        from ui.interface import launch_gui
        launch_gui()
        return

    memory.init_db()
    log.info(f"{ASSISTANT_NAME} starting (voice={args.voice})")

    try:
        if args.voice:
            run_voice_loop()
        else:
            run_text_loop()
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        print(f"SHADOW hit an unexpected error and needs to stop: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
