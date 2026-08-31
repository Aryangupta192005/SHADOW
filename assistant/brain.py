"""
brain.py
--------
Understands natural language and produces a structured "Intent".

Two modes:
1. Rule-based (default, no API key needed) — regex/keyword matching
   covering the Milestone 1 command set. Deterministic and offline.
2. LLM-assisted (optional) — if config.LLM_API_KEY is set, ambiguous
   or complex requests are sent to the LLM with the tool registry's
   specs, and the LLM returns a structured plan directly.

The brain NEVER executes anything. It only returns data structures
that the planner/executor consume. This keeps "understanding"
strictly separated from "acting".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from assistant.logger import get_logger
from assistant.tool_registry import tool_specs
from config import LLM_API_KEY, LLM_MODEL

log = get_logger("brain")


@dataclass
class Intent:
    goal: str                       # human-readable summary of what the user wants
    steps: list[dict[str, Any]] = field(default_factory=list)  # [{tool, arguments}]
    needs_clarification: bool = False
    clarification_question: str | None = None
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Rule-based parsing (Milestone 1)
# ---------------------------------------------------------------------------

_APP_OPEN_RE = re.compile(r"^\s*(?:open|launch|start)\s+(.+?)\s*$", re.IGNORECASE)
_APP_CLOSE_RE = re.compile(r"^\s*(?:close|quit|exit)\s+(.+?)\s*$", re.IGNORECASE)
_WEBSITE_RE = re.compile(
    r"^\s*(?:open|go to|visit)\s+(?:website\s+)?(https?://\S+|[\w.-]+\.\w{2,})\s*$",
    re.IGNORECASE,
)
_FOLDER_RE = re.compile(
    r"^\s*(?:create|make)\s+(?:a\s+)?folder\s+(?:called\s+|named\s+)?['\"]?([^'\"]+?)['\"]?"
    r"(?:\s+(?:in|at)\s+(.+))?\s*$",
    re.IGNORECASE,
)
_SEARCH_RE = re.compile(
    r"^\s*(?:find|search for|search)\s+(?:all\s+)?(.+?)\s+(?:in|inside)\s+(.+?)\s*$",
    re.IGNORECASE,
)
_READ_RE = re.compile(r"^\s*(?:read|open and read)\s+(?:the\s+file\s+)?(.+?)\s*$", re.IGNORECASE)

_EXT_HINTS = {
    "pdf": "*.pdf", "pdfs": "*.pdf",
    "python file": "*.py", "python files": "*.py",
    "image": "*.png", "images": "*.png",
    "text file": "*.txt", "text files": "*.txt",
    "word document": "*.docx", "word documents": "*.docx",
    "excel file": "*.xlsx", "excel files": "*.xlsx",
}

# Common shorthand folder names -> a placeholder the executor can expand
# using the OS user profile at execution time (kept as a string here;
# resolved downstream, not hardcoded to one user's absolute path).
_KNOWN_DIRS = {
    "downloads": "~/Downloads",
    "documents": "~/Documents",
    "desktop": "~/Desktop",
    "pictures": "~/Pictures",
}


def _resolve_dir_phrase(phrase: str) -> str:
    key = phrase.strip().lower()
    return _KNOWN_DIRS.get(key, phrase.strip())


def _resolve_pattern_phrase(phrase: str) -> str:
    key = phrase.strip().lower()
    if key in _EXT_HINTS:
        return _EXT_HINTS[key]
    if phrase.strip().startswith("*."):
        return phrase.strip()
    return f"*{phrase.strip()}*"


def _rule_based_parse(text: str) -> Intent | None:
    text = text.strip()

    if m := _WEBSITE_RE.match(text):
        url = m.group(1)
        if not url.startswith("http"):
            url = f"https://{url}"
        return Intent(goal=f"Open website {url}", steps=[
            {"tool": "open_website", "arguments": {"url": url}}
        ], raw_text=text)

    if m := _FOLDER_RE.match(text):
        name, location = m.group(1), m.group(2)
        base = _resolve_dir_phrase(location) if location else "~/Desktop"
        path = f"{base.rstrip('/')}/{name.strip()}"
        return Intent(goal=f"Create folder '{name.strip()}'", steps=[
            {"tool": "create_folder", "arguments": {"path": path}}
        ], raw_text=text)

    if m := _SEARCH_RE.match(text):
        what, where = m.group(1), m.group(2)
        pattern = _resolve_pattern_phrase(what)
        directory = _resolve_dir_phrase(where)
        return Intent(goal=f"Search for {what.strip()} in {where.strip()}", steps=[
            {"tool": "search_files", "arguments": {"directory": directory, "pattern": pattern, "recursive": True}}
        ], raw_text=text)

    if m := _APP_CLOSE_RE.match(text):
        return Intent(goal=f"Close {m.group(1).strip()}", steps=[
            {"tool": "close_application", "arguments": {"name": m.group(1).strip()}}
        ], raw_text=text)

    if m := _APP_OPEN_RE.match(text):
        name = m.group(1).strip()
        return Intent(goal=f"Open {name}", steps=[
            {"tool": "smart_open", "arguments": {"query": name}}
        ], raw_text=text)

    if m := _READ_RE.match(text):
        return Intent(goal=f"Read {m.group(1).strip()}", steps=[
            {"tool": "read_file", "arguments": {"path": m.group(1).strip()}}
        ], raw_text=text)

    return None


# ---------------------------------------------------------------------------
# Optional LLM-assisted parsing
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are the planning brain of SHADOW, a Windows desktop automation assistant.
Convert the user's request into a JSON object with this exact shape:

{
  "goal": "short human-readable summary",
  "steps": [ { "tool": "tool_name", "arguments": { ... } } ],
  "needs_clarification": false,
  "clarification_question": null
}

Only use tools from this list (name: description / parameters):
""" + "\n".join(
    f"- {t['name']}: {t['description']} / params={t['parameters']}" for t in tool_specs()
) + """

Rules:
- Only call tools from the list above. Never invent a tool name.
- If the request is ambiguous or missing required info, set needs_clarification=true
  and ask ONE specific question in clarification_question; leave steps empty.
- Keep plans as short as possible while fully satisfying the request.
- Respond with ONLY the JSON object. No markdown, no commentary.
"""


def _llm_parse(text: str) -> Intent | None:
    if not LLM_API_KEY:
        return None

    try:
        import requests
    except ImportError:
        log.warning("`requests` not installed; skipping LLM parse.")
        return None

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": 1024,
                "system": _SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": text}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        raw = "".join(text_blocks).strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
        return Intent(
            goal=parsed.get("goal", text),
            steps=parsed.get("steps", []),
            needs_clarification=parsed.get("needs_clarification", False),
            clarification_question=parsed.get("clarification_question"),
            raw_text=text,
        )
    except Exception as e:
        log.error(f"LLM parse failed, falling back to rule-based: {e}")
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def understand(text: str) -> Intent:
    """Main entry point: text in, Intent out."""
    text = (text or "").strip()
    if not text:
        return Intent(goal="", needs_clarification=True,
                       clarification_question="I didn't catch that — what would you like me to do?",
                       raw_text=text)

    intent = _rule_based_parse(text)
    if intent:
        log.info(f"Rule-based match: {intent.goal}")
        return intent

    llm_intent = _llm_parse(text)
    if llm_intent:
        log.info(f"LLM parse: {llm_intent.goal}")
        return llm_intent

    return Intent(
        goal=text,
        needs_clarification=True,
        clarification_question=(
            "I'm not sure how to do that yet. Could you rephrase, "
            "e.g. 'open Chrome', 'create folder Projects', or "
            "'find PDFs in Downloads'?"
        ),
        raw_text=text,
    )