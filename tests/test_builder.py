from types import SimpleNamespace

import pytest

from studio_runner import builder
from studio_runner import config as config_module
from studio_runner.config import Config


@pytest.mark.parametrize(
    ("windows", "shell_tool"),
    [(False, "Bash"), (True, "PowerShell")],
)
def test_builder_uses_restricted_exact_allowlist(monkeypatch, tmp_path, windows, shell_tool):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured.update(kwargs)
        return SimpleNamespace(stdout="STATUS\nPASS", stderr="", returncode=0)

    monkeypatch.setattr(builder, "run", fake_run)
    monkeypatch.setattr(config_module, "is_windows", lambda: windows)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "paid-fallback")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "gateway-fallback")
    monkeypatch.setenv("VENICE_API_KEY", "reviewer-secret")
    monkeypatch.setenv("CLAUDE_CODE_USE_BEDROCK", "1")
    monkeypatch.setenv("A3A_TEST_SENTINEL", "preserved")

    issue = SimpleNamespace(number=17, title="Safe verification", body="Run the tests")
    policy = Config({}, tmp_path / "studio.yaml").builder_policy
    result = builder.run_builder(tmp_path, issue, policy)

    cmd = captured["cmd"]
    assert result == "STATUS\nPASS"
    assert cmd[:3] == ["claude", "-p", "--restricted"]
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    assert "--add-dir" not in cmd
    assert "--dangerously-skip-permissions" not in cmd
    assert "bypassPermissions" not in cmd
    assert "--strict-mcp-config" in cmd
    assert "--no-chrome" in cmd
    assert "--no-session-persistence" in cmd

    tools = cmd[cmd.index("--tools") + 1].split(",")
    allowed = cmd[cmd.index("--allowedTools") + 1].split(",")
    denied = cmd[cmd.index("--disallowedTools") + 1].split(",")
    assert tools == ["Read", "Glob", "Grep", "Edit", "Write", shell_tool]
    assert shell_tool not in allowed
    assert all("*" not in rule for rule in allowed)
    assert f"{shell_tool}(python -m pytest)" in allowed
    assert f"{shell_tool}(npm run build)" in allowed
    assert f"{shell_tool}(cat *)" in denied
    assert f"{shell_tool}(git *)" in denied

    other_shell_tool = "PowerShell" if shell_tool == "Bash" else "Bash"
    assert not any(rule.startswith(other_shell_tool) for rule in tools)
    assert not any(rule.startswith(other_shell_tool) for rule in allowed)
    assert not any(rule.startswith(other_shell_tool) for rule in denied)

    env = captured["env"]
    assert "ANTHROPIC_API_KEY" not in env
    assert "ANTHROPIC_AUTH_TOKEN" not in env
    assert "VENICE_API_KEY" not in env
    assert "CLAUDE_CODE_USE_BEDROCK" not in env
    assert env["A3A_TEST_SENTINEL"] == "preserved"
    assert captured["cwd"] == tmp_path
    assert captured["check"] is False
