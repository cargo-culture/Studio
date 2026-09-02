import json
import pytest
from studio_runner import config as config_module
from studio_runner.config import load_config
from studio_runner.util import StudioError


def _write_template_config(tmp_path):
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(json.dumps({"studio":{"canonical_branch":"main"},"review":{"max_builder_reviewer_rounds":2}}))


def test_template_config_loads(tmp_path):
    _write_template_config(tmp_path)
    c = load_config(tmp_path)
    assert c.canonical_branch == "main"
    assert c.max_review_rounds == 2
    assert c.builder_policy.permission_mode == "dontAsk"
    assert c.builder_policy.restricted_to_worktree is True


def test_builder_policy_selects_bash_on_non_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "is_windows", lambda: False)
    _write_template_config(tmp_path)
    policy = load_config(tmp_path).builder_policy

    assert policy.tools == ("Read", "Glob", "Grep", "Edit", "Write", "Bash")
    assert "Bash(python -m pytest)" in policy.allowed_tools
    assert "Bash(npm run build)" in policy.allowed_tools
    assert "Bash(cat *)" in policy.denied_tools
    assert "Bash(git *)" in policy.denied_tools
    assert not any(rule.startswith("PowerShell") for rule in policy.allowed_tools)
    assert not any(rule.startswith("PowerShell") for rule in policy.denied_tools)
    assert "PowerShell(Get-Content *)" not in policy.denied_tools
    assert "PowerShell(Get-ChildItem *)" not in policy.denied_tools


def test_builder_policy_selects_powershell_on_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "is_windows", lambda: True)
    _write_template_config(tmp_path)
    policy = load_config(tmp_path).builder_policy

    assert policy.tools == ("Read", "Glob", "Grep", "Edit", "Write", "PowerShell")
    assert "PowerShell(python -m pytest)" in policy.allowed_tools
    assert "PowerShell(npm run build)" in policy.allowed_tools
    assert "PowerShell(cat *)" in policy.denied_tools
    assert "PowerShell(git *)" in policy.denied_tools
    assert not any(rule.startswith("Bash") for rule in policy.allowed_tools)
    assert not any(rule.startswith("Bash") for rule in policy.denied_tools)
    assert "Read" in policy.allowed_tools and "Write" in policy.allowed_tools

    for cmdlet in (
        "Get-Content",
        "Get-ChildItem",
        "Get-Item",
        "Resolve-Path",
        "Test-Path",
        "Select-String",
        "Invoke-WebRequest",
        "Invoke-RestMethod",
        "Invoke-Expression",
        "Start-Process",
    ):
        assert f"PowerShell({cmdlet} *)" in policy.denied_tools
    assert "PowerShell(Get-Location)" in policy.denied_tools
    assert "PowerShell(Get-Variable)" in policy.denied_tools
    assert "PowerShell(Get-Variable *)" in policy.denied_tools
    assert "PowerShell(powershell *)" in policy.denied_tools
    assert "PowerShell(pwsh *)" in policy.denied_tools
    assert "PowerShell(cmd *)" in policy.denied_tools


@pytest.mark.parametrize("windows", [False, True])
@pytest.mark.parametrize(
    "permissions",
    [
        {"mode": "bypassPermissions"},
        {"mode": "acceptEdits"},
        {"restricted_to_worktree": False},
        {"tools": ["Read", "Glob", "Grep", "Edit", "Write", "Bash", "PowerShell"]},
        {"allow": ["Read", "Glob", "Grep", "Edit", "Write", "Bash"]},
        {"allow": ["Read", "Glob", "Grep", "Edit", "Write", "PowerShell"]},
        {"allow": ["Read", "Glob", "Grep", "Edit", "Write", "Bash(pytest *)"]},
        {"allow": ["Read", "Glob", "Grep", "Edit", "Write", "PowerShell(pytest *)"]},
    ],
)
def test_builder_policy_rejects_broader_permissions(tmp_path, monkeypatch, permissions, windows):
    monkeypatch.setattr(config_module, "is_windows", lambda: windows)
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps({"agents": {"builder": {"permissions": permissions}}})
    )

    with pytest.raises(StudioError):
        load_config(tmp_path).builder_policy


def test_builder_policy_rejects_non_native_shell_tool_selection(tmp_path, monkeypatch):
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps(
            {
                "agents": {
                    "builder": {
                        "permissions": {
                            "tools": ["Read", "Glob", "Grep", "Edit", "Write", "Bash"]
                        }
                    }
                }
            }
        )
    )

    monkeypatch.setattr(config_module, "is_windows", lambda: True)
    with pytest.raises(StudioError):
        load_config(tmp_path).builder_policy

    monkeypatch.setattr(config_module, "is_windows", lambda: False)
    assert load_config(tmp_path).builder_policy.tools == (
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Bash",
    )


def test_builder_policy_rejects_unrecognized_shell_override_key(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "is_windows", lambda: True)
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps({"agents": {"builder": {"permissions": {"shell": "Bash"}}}})
    )

    with pytest.raises(StudioError):
        load_config(tmp_path).builder_policy
