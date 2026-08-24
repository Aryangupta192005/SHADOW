import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assistant.brain import Intent
from assistant.planner import build_plan


def test_build_plan_from_valid_intent():
    intent = Intent(
        goal="Open Chrome",
        steps=[{"tool": "open_application", "arguments": {"name": "chrome"}}],
    )
    plan = build_plan(intent)
    assert plan.valid is True
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "open_application"


def test_build_plan_rejects_unknown_tool():
    intent = Intent(
        goal="Do something weird",
        steps=[{"tool": "not_a_real_tool", "arguments": {}}],
    )
    plan = build_plan(intent)
    assert plan.valid is False
    assert "unknown tool" in plan.error.lower()


def test_build_plan_handles_clarification_needed():
    intent = Intent(goal="", needs_clarification=True,
                     clarification_question="What do you want me to do?")
    plan = build_plan(intent)
    assert plan.valid is False
    assert plan.error == "What do you want me to do?"


def test_build_plan_rejects_empty_steps():
    intent = Intent(goal="Nothing to do", steps=[])
    plan = build_plan(intent)
    assert plan.valid is False


def test_build_plan_expands_home_shorthand():
    intent = Intent(
        goal="Search downloads",
        steps=[{"tool": "search_files", "arguments": {"directory": "~/Downloads", "pattern": "*.pdf"}}],
    )
    plan = build_plan(intent)
    assert plan.valid is True
    assert "~" not in plan.steps[0].arguments["directory"]
