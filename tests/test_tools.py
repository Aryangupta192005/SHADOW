import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assistant.tool_registry import TOOLS, get_tool, list_tools, tool_specs


def test_all_tools_are_callable():
    for name, fn in TOOLS.items():
        assert callable(fn), f"{name} is not callable"


def test_get_tool_returns_none_for_unknown():
    assert get_tool("definitely_not_a_real_tool") is None


def test_get_tool_returns_registered_function():
    assert get_tool("open_application") is not None


def test_list_tools_sorted_and_matches_registry():
    names = list_tools()
    assert names == sorted(TOOLS.keys())
    assert set(names) == set(TOOLS.keys())


def test_tool_specs_cover_every_registered_tool():
    spec_names = {s["name"] for s in tool_specs()}
    assert spec_names == set(TOOLS.keys()), (
        "Every registered tool must have a spec for LLM tool-calling, "
        "and every spec must correspond to a real registered tool."
    )
