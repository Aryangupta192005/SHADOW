"""
executor.py
-----------
Runs a Plan produced by the planner:

  for step in plan:
      safety_check(step)
      if needs confirmation: ask user (via injected callback)
      result = call the tool
      status  = observer.verify(...)
      record + continue/stop

The executor is UI-agnostic: it takes a `confirm_callback(prompt) -> bool`
so the same executor works for the text console, GUI, or voice interface.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable

from assistant.logger import get_logger
from assistant.observer import verify
from assistant.planner import Plan, PlanStep
from assistant.safety import RiskLevel, classify, describe_action
from assistant.tool_registry import get_tool
from config import MAX_STEP_RETRIES

log = get_logger("executor")

ConfirmCallback = Callable[[str], bool]


def _default_confirm(prompt: str) -> bool:
    """Fallback confirmation via plain input() — used if no callback is injected."""
    answer = input(f"{prompt} [yes/no]: ").strip().lower()
    return answer in ("y", "yes")


@dataclass
class StepReport:
    step_id: int
    tool: str
    arguments: dict
    risk: str
    confirmed: bool
    success: bool
    message: str
    retries_used: int = 0


@dataclass
class ExecutionReport:
    goal: str
    step_reports: list[StepReport] = field(default_factory=list)
    stopped_early: bool = False
    stop_reason: str | None = None

    @property
    def all_succeeded(self) -> bool:
        return all(r.success for r in self.step_reports) and not self.stopped_early


def execute_plan(
    plan: Plan,
    confirm_callback: ConfirmCallback | None = None,
    stop_event: "threading.Event | None" = None,
) -> ExecutionReport:
    """Run every step in `plan`.

    `stop_event` is an optional threading.Event a caller (e.g. the GUI's
    Stop button) can set from another thread. It's checked before each
    step starts, so execution halts cleanly between steps rather than
    mid-action — SHADOW never interrupts a tool call in flight.
    """
    confirm = confirm_callback or _default_confirm
    report = ExecutionReport(goal=plan.goal)

    if not plan.valid:
        report.stopped_early = True
        report.stop_reason = plan.error
        return report

    for step in plan.steps:
        if stop_event is not None and stop_event.is_set():
            report.stopped_early = True
            report.stop_reason = "Stopped by user before all steps completed."
            log.info(report.stop_reason)
            break

        step_report = _execute_step(step, confirm)
        report.step_reports.append(step_report)

        if not step_report.success:
            report.stopped_early = True
            report.stop_reason = f"Step {step.step_id} ({step.tool}) failed: {step_report.message}"
            log.warning(report.stop_reason)
            break

    return report


def _execute_step(step: PlanStep, confirm: ConfirmCallback) -> StepReport:
    decision = classify(step.tool, step.arguments)

    if decision.requires_confirmation:
        description = describe_action(step.tool, step.arguments)
        approved = confirm(
            f"This action is {decision.risk.value} risk: {description}. Continue?"
        )
        if not approved:
            return StepReport(
                step_id=step.step_id, tool=step.tool, arguments=step.arguments,
                risk=decision.risk.value, confirmed=False, success=False,
                message="User declined confirmation.",
            )

    tool_fn = get_tool(step.tool)
    if tool_fn is None:
        return StepReport(
            step_id=step.step_id, tool=step.tool, arguments=step.arguments,
            risk=decision.risk.value, confirmed=decision.requires_confirmation,
            success=False, message=f"Tool '{step.tool}' is not registered.",
        )

    # Delete tools require an explicit confirmed flag as a second layer of defense.
    call_args = dict(step.arguments)
    if step.tool in ("delete_file", "delete_folder"):
        call_args["confirmed"] = True

    retries_used = 0
    last_result = {"success": False, "message": "not executed"}

    while retries_used <= MAX_STEP_RETRIES:
        try:
            last_result = tool_fn(**call_args)
        except Exception as e:
            last_result = {"success": False, "message": f"Unhandled error: {e}"}
            log.error(f"Step {step.step_id} ({step.tool}) raised: {e}")

        verification = verify(step.tool, step.arguments, last_result)
        if verification.success:
            log.info(f"Step {step.step_id} ({step.tool}) succeeded: {verification.message}")
            return StepReport(
                step_id=step.step_id, tool=step.tool, arguments=step.arguments,
                risk=decision.risk.value, confirmed=decision.requires_confirmation,
                success=True, message=verification.message, retries_used=retries_used,
            )

        retries_used += 1
        if retries_used <= MAX_STEP_RETRIES:
            log.info(f"Step {step.step_id} ({step.tool}) failed, retrying "
                      f"({retries_used}/{MAX_STEP_RETRIES}): {verification.message}")

    return StepReport(
        step_id=step.step_id, tool=step.tool, arguments=step.arguments,
        risk=decision.risk.value, confirmed=decision.requires_confirmation,
        success=False, message=verification.message, retries_used=retries_used,
    )
