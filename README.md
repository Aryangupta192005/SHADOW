# SHADOW — Personal AI Desktop Assistant

SHADOW is a Windows desktop assistant built around one loop:

```
UNDERSTAND → PLAN → SAFETY CHECK → ACT → OBSERVE → VERIFY → RESPOND
```

It doesn't just answer questions — it opens apps, manages files, and
(in later milestones) drives the browser, keyboard, and mouse, always
through a safety layer that gates anything risky behind confirmation.

## Status: Milestone 1 (text assistant) — working and tested

Currently supported, all through natural language in the console:

- `open Chrome` / `open VS Code` / `close Chrome` — application control
- `open website github.com` — opens your default browser
- `create folder called Projects in Downloads` — folder management
- `find PDFs in Downloads` / `find *.py in Documents` — file search
- `read <path>` — read a text file

Every action is risk-classified (LOW / MEDIUM / HIGH) before it runs.
HIGH-risk actions (delete, terminal commands matching destructive
patterns, etc.) always stop and ask for explicit confirmation —
there's no way to bypass this from a prompt.

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # then edit .env if you want LLM-assisted parsing
python main.py
```

SHADOW runs with **zero required API keys** — the default mode is a
rule-based parser covering the Milestone 1 command set. Set
`LLM_API_KEY` in `.env` to additionally let an LLM handle requests the
rule-based parser doesn't recognize (falls back automatically).

## Project layout

```
SHADOW/
├── main.py                 # entry point / text (and voice) loop
├── config.py                # env vars, paths, safety toggles
├── assistant/
│   ├── brain.py              # NL -> Intent (rule-based + optional LLM)
│   ├── planner.py            # Intent -> validated Plan
│   ├── executor.py           # runs a Plan through safety + tools + observer
│   ├── safety.py             # LOW/MEDIUM/HIGH risk classification
│   ├── observer.py           # verifies steps actually succeeded
│   ├── tool_registry.py      # the ONLY tools the AI may call
│   ├── memory.py             # SQLite persistent memory
│   ├── input_processor.py    # normalizes text/voice input
│   ├── response.py           # formats + optionally speaks results
│   └── logger.py             # shared logging (never logs secrets)
├── tools/
│   ├── applications.py       # open/close/discover apps
│   ├── files.py               # search/create/move/copy/rename/delete
│   └── browser.py             # open_website (Playwright lands in M4)
├── voice/                    # Milestone 2 (stubs wired in, fail gracefully)
├── ui/                       # Milestone 7 (PySide6 GUI, stub)
├── tests/                    # pytest, uses temp dirs only — never touches real files
└── database/shadow.db        # created on first run
```

## Safety model

| Risk   | Examples                                             | Behavior                      |
|--------|-------------------------------------------------------|--------------------------------|
| LOW    | open app, search files, read file, open website        | runs immediately               |
| MEDIUM | move/copy/rename file, close app, run benign terminal cmd | runs immediately (configurable) |
| HIGH   | delete file/folder, destructive terminal commands, shutdown/restart | always asks for confirmation, no bypass |

Unknown tools default to HIGH risk. Delete operations additionally
require an explicit `confirmed=True` flag set only by the executor
after the safety check passes — a second layer of defense even if
something upstream misclassifies risk.

## Running tests

```bash
pytest tests/ -v
```

Tests use `tmp_path` fixtures exclusively — nothing in `tests/` ever
touches real user files.

## Roadmap

- [x] **M1** — text assistant: apps, websites, folders, file search
- [ ] **M2** — voice input (Whisper) + voice output (pyttsx3/edge-tts)
- [ ] **M3** — LLM tool-calling, multi-step task planning
- [ ] **M4** — Playwright browser automation, keyboard/mouse control
- [ ] **M5** — screenshots + vision-based verification for GUI actions
- [ ] **M6** — richer memory, conversational context, error recovery
- [ ] **M7** — PySide6 desktop GUI, wake word, background mode

`voice/` and `ui/` already contain the module shells these milestones
will fill in, so nothing above them needs to change as they land.

## Notes on Windows-only tools

`tools/applications.py` and parts of `tools/files.py` (`os.startfile`)
are Windows-specific by design (this is a Windows desktop assistant).
They fail gracefully with a clear message rather than crashing when
run on another OS — which is how the test suite runs them in CI.
