import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assistant.safety import RiskLevel, classify


def test_open_application_is_low_risk():
    decision = classify("open_application", {"name": "chrome"})
    assert decision.risk == RiskLevel.LOW
    assert decision.requires_confirmation is False


def test_delete_file_is_high_risk_and_requires_confirmation():
    decision = classify("delete_file", {"path": "C:/Users/test/file.txt"})
    assert decision.risk == RiskLevel.HIGH
    assert decision.requires_confirmation is True


def test_unknown_tool_defaults_to_high_risk():
    decision = classify("some_unregistered_tool", {})
    assert decision.risk == RiskLevel.HIGH
    assert decision.requires_confirmation is True


def test_terminal_command_with_destructive_pattern_is_high_risk():
    decision = classify("run_terminal_command", {"command": "del C:\\Users\\test\\*.*"})
    assert decision.risk == RiskLevel.HIGH
    assert decision.requires_confirmation is True


def test_terminal_command_benign_is_medium_risk():
    decision = classify("run_terminal_command", {"command": "python --version"})
    assert decision.risk == RiskLevel.MEDIUM


def test_search_files_is_low_risk():
    decision = classify("search_files", {"directory": "~/Downloads", "pattern": "*.pdf"})
    assert decision.risk == RiskLevel.LOW
    assert decision.requires_confirmation is False
