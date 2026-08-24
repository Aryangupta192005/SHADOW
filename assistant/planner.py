"""
planner.py
----------
Takes the Intent produced by brain.py and turns it into a validated,
structured Plan the executor can run step by step.

For Milestone 1 the brain already emits near-final steps for
single-action requests, so the planner's job is mostly:
  - validate each step references a real, registered tool
  - attach a step id and default status
  - enforce MAX_PLAN_STEPS
  - expand '~' home-directory shorthands left in arguments

Multi-step composite planning (e.g. "prepare my Python project")
is a Milestone 3 concern, but the data structure here is already
shaped to support it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from assistant.brain import Intent
from assistant.logger import get_logger
from assistant.tool_registry import get_tool
from config import MAX_PLAN_STEPS

log = get_logger("planner")


@dataclass
class PlanStep:
    step_id: int
    tool: str
    arguments: dict[str, Any]
    status: str = "pending"  # pending | running | success | failed | skipped


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    valid: bool = True
    error: str | None = None


def _expand_path_args(arguments: dict[str, Any]) -> dict[str, Any]:
    expanded = {}
    for k, v in arguments.items():
        if isinstance(v, str) and ("~" in v or v.startswith("$")):
            expanded[k] = os.path.expanduser(os.path.expandvars(v))
        else:
            expanded[k] = v
    return expanded


def build_plan(intent: Intent) -> Plan:
    if intent.needs_clarification:
        return Plan(goal=intent.goal, valid=False, error=intent.clarification_question)

    if not intent.steps:
        return Plan(goal=intent.goal, valid=False, error="No actionable steps were produced.")

    if len(intent.steps) > MAX_PLAN_STEPS:
        return Plan(
            goal=intent.goal, valid=False,
            error=f"Plan has {len(intent.steps)} steps, exceeding the safety limit of {MAX_PLAN_STEPS}.",
        )

    steps: list[PlanStep] = []
    for i, raw_step in enumerate(intent.steps, start=1):
        tool_name = raw_step.get("tool")
        arguments = _expand_path_args(raw_step.get("arguments", {}))

        if not tool_name or get_tool(tool_name) is None:
            return Plan(
                goal=intent.goal, valid=False,
                error=f"Step {i} references unknown tool '{tool_name}'.",
            )

        steps.append(PlanStep(step_id=i, tool=tool_name, arguments=arguments))

    plan = Plan(goal=intent.goal, steps=steps)
    log.info(f"Built plan '{plan.goal}' with {len(plan.steps)} step(s).")
    return plan
