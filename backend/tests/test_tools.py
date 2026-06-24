from app.security.permissions import privacy_context
from app.tools.calculator import safe_calculate
from app.tools.registry import default_registry
from app.tools.source_compare import ClaimItem, compare_claims


def test_calculator_safe_eval():
    assert safe_calculate("2 * (3 + 4)") == 14
    assert safe_calculate("sqrt(144)") == 12
    assert round(safe_calculate("log(e)"), 6) == 1.0


def test_calculator_rejects_unsafe():
    import pytest
    with pytest.raises(Exception):
        safe_calculate("__import__('os').system('ls')")


def test_registry_has_all_tools():
    reg = default_registry()
    names = reg.names()
    for expected in [
        "web_search", "read_url", "calculator", "memory_save", "memory_search",
        "memory_list", "memory_delete", "local_file_ingest", "local_file_search",
        "compare_sources", "create_task_plan", "safe_code_runner", "datetime",
        "system_health",
    ]:
        assert expected in names


def test_calculator_tool_via_registry():
    reg = default_registry()
    res = reg.call("calculator", {"expression": "10 / 4"})
    assert res.ok
    assert res.data["result"] == 2.5
    # traced
    assert reg.trace[-1].tool == "calculator"


def test_unknown_tool_fails_gracefully():
    reg = default_registry()
    res = reg.call("nope", {})
    assert not res.ok
    assert "Unknown tool" in res.error


def test_code_runner_requires_permission():
    reg = default_registry()  # no code_exec by default
    res = reg.call("safe_code_runner", {"code": "print(1+1)"})
    assert not res.ok
    assert "permission" in res.error.lower()


def test_code_runner_with_permission_and_blocks_danger():
    reg = default_registry(privacy_context(local_privacy=False, allow_code=True))
    ok = reg.call("safe_code_runner", {"code": "print(sum(range(5)))"})
    assert ok.ok
    assert ok.data["stdout"].strip() == "10"
    danger = reg.call("safe_code_runner", {"code": "import os\nos.system('ls')"})
    assert not danger.ok


def test_compare_sources_detects_contradiction():
    claims = [
        ClaimItem(source_id="S1", text="The feature is supported and stable"),
        ClaimItem(source_id="S2", text="The feature is unsupported and deprecated"),
    ]
    result = compare_claims(claims)
    assert result["has_conflict"]


def test_datetime_and_system_health():
    reg = default_registry()
    assert reg.call("datetime", {}).ok
    h = reg.call("system_health", {})
    assert h.ok
    assert h.data["model_provider"]
