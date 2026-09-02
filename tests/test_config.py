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

    # Every argument-free (no wildcard) Windows-only denial, including the
    # PowerShell alias/secondary-shell entries, must be entirely absent
    # off Windows: none of it is native PowerShell tool syntax.
    for rule in config_module.BUILDER_DENIED_TOOLS_WINDOWS_ONLY:
        if "*" not in rule:
            assert rule not in policy.denied_tools


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
        "Get-ItemProperty",
        "Get-Acl",
        "Get-Process",
        "Get-Service",
        "Get-NetTCPConnection",
    ):
        assert f"PowerShell({cmdlet} *)" in policy.denied_tools
    assert "PowerShell(Get-Location)" in policy.denied_tools
    assert "PowerShell(Get-Variable)" in policy.denied_tools
    assert "PowerShell(Get-Variable *)" in policy.denied_tools
    assert "PowerShell(Get-Process)" in policy.denied_tools
    assert "PowerShell(Get-Service)" in policy.denied_tools
    assert "PowerShell(Get-NetTCPConnection)" in policy.denied_tools
    assert "PowerShell(powershell *)" in policy.denied_tools
    assert "PowerShell(pwsh *)" in policy.denied_tools
    assert "PowerShell(cmd *)" in policy.denied_tools
    # Bare (argument-free) invocations of the native shell tools themselves,
    # which are not covered by the `*` (one-or-more-argument) wildcard rules.
    assert "PowerShell(powershell)" in policy.denied_tools
    assert "PowerShell(pwsh)" in policy.denied_tools
    assert "PowerShell(cmd)" in policy.denied_tools

    for alias in ("gc *", "type *", "gci *", "dir *", "gi *", "rvpa *", "sls *", "iwr *", "irm *", "iex *", "saps *", "gp *", "ps *", "gsv *"):
        assert f"PowerShell({alias})" in policy.denied_tools
    for bare in ("gl", "pwd", "gv", "ps", "gsv"):
        assert f"PowerShell({bare})" in policy.denied_tools
    assert "PowerShell(gv *)" in policy.denied_tools
    for shell in ("bash", "sh", "wsl"):
        assert f"PowerShell({shell})" in policy.denied_tools
        assert f"PowerShell({shell} *)" in policy.denied_tools


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


@pytest.mark.parametrize("windows", [False, True])
def test_builder_policy_rejects_tools_key_unconditionally(tmp_path, monkeypatch, windows):
    # "tools" is not a configurable permission key at all, even when its
    # value exactly matches the platform's fixed native tool set: only the
    # key's presence is checked (via BUILDER_PERMISSION_KEYS), never its value.
    monkeypatch.setattr(config_module, "is_windows", lambda: windows)
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

    with pytest.raises(StudioError, match="unrecognized Builder permission key"):
        load_config(tmp_path).builder_policy


@pytest.mark.parametrize("windows", [False, True])
def test_builder_policy_rejects_allow_key_unconditionally(tmp_path, monkeypatch, windows):
    # "allow" is not configurable either, even with a value identical to the
    # platform's native allowlist: presence of the key alone is rejected.
    monkeypatch.setattr(config_module, "is_windows", lambda: windows)
    shell_tool = "PowerShell" if windows else "Bash"
    native_allowed = config_module._for_shell(config_module.BUILDER_ALLOWED_TOOLS, shell_tool)
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps({"agents": {"builder": {"permissions": {"allow": list(native_allowed)}}}})
    )

    with pytest.raises(StudioError, match="unrecognized Builder permission key"):
        load_config(tmp_path).builder_policy


def test_builder_policy_deny_only_appends_on_non_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "is_windows", lambda: False)
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps({"agents": {"builder": {"permissions": {"deny": ["Bash(rm -rf *)"]}}}})
    )

    policy = load_config(tmp_path).builder_policy

    assert "Bash(rm -rf *)" in policy.denied_tools
    for native_rule in config_module.BUILDER_DENIED_TOOLS:
        assert native_rule in policy.denied_tools


def test_builder_policy_deny_only_appends_on_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "is_windows", lambda: True)
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps({"agents": {"builder": {"permissions": {"deny": ["PowerShell(Remove-Item *)"]}}}})
    )

    policy = load_config(tmp_path).builder_policy

    assert "PowerShell(Remove-Item *)" in policy.denied_tools
    for native_rule in config_module.BUILDER_DENIED_TOOLS:
        translated = config_module._for_shell((native_rule,), "PowerShell")[0]
        assert translated in policy.denied_tools
    for native_rule in config_module.BUILDER_DENIED_TOOLS_WINDOWS_ONLY:
        assert native_rule in policy.denied_tools


def test_builder_policy_deny_translates_canonical_bash_form_on_windows(tmp_path, monkeypatch):
    # Configured deny rules are authored in canonical Bash(...) source form
    # on every host, including Windows, and must be translated through
    # `_for_shell` to the native PowerShell(...) form before merging, the
    # same way the built-in BUILDER_DENIED_TOOLS rules are.
    monkeypatch.setattr(config_module, "is_windows", lambda: True)
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps({"agents": {"builder": {"permissions": {"deny": ["Bash(rm -rf *)"]}}}})
    )

    policy = load_config(tmp_path).builder_policy

    assert "PowerShell(rm -rf *)" in policy.denied_tools
    assert "Bash(rm -rf *)" not in policy.denied_tools
    assert not any(rule.startswith("Bash") for rule in policy.denied_tools)


def test_builder_policy_rejects_unrecognized_shell_override_key(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "is_windows", lambda: True)
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps({"agents": {"builder": {"permissions": {"shell": "Bash"}}}})
    )

    with pytest.raises(StudioError):
        load_config(tmp_path).builder_policy


def test_for_shell_does_not_translate_unrelated_tool_with_bash_prefix():
    # `_for_shell` must only rewrite the exact "Bash" tool name and rules
    # that start with the literal "Bash(" prefix. A distinct tool name that
    # merely starts with the substring "Bash" (e.g. a hypothetical
    # "BashHelper" tool) must pass through untouched, not be misdetected as
    # a Bash shell rule and rewritten to "PowerShellHelper(x)".
    rules = ("BashHelper(x)", "BashHelper", "Bash(python -m pytest)", "Bash")
    translated = config_module._for_shell(rules, "PowerShell")

    assert translated == (
        "BashHelper(x)",
        "BashHelper",
        "PowerShell(python -m pytest)",
        "PowerShell",
    )


def test_windows_only_denials_do_not_duplicate_translated_posix_denials():
    # BUILDER_DENIED_TOOLS_WINDOWS_ONLY exists to add PowerShell-native
    # denials that the POSIX->PowerShell translation of BUILDER_DENIED_TOOLS
    # cannot express. It must never repeat a rule the translation already
    # produces, since `_unique` would silently make the duplicate a no-op
    # and the constant would misrepresent the actual added coverage.
    translated_posix = set(config_module._for_shell(config_module.BUILDER_DENIED_TOOLS, "PowerShell"))
    windows_only = set(config_module.BUILDER_DENIED_TOOLS_WINDOWS_ONLY)

    assert translated_posix & windows_only == set()
    # The constant itself must also be duplicate-free.
    assert len(config_module.BUILDER_DENIED_TOOLS_WINDOWS_ONLY) == len(windows_only)
