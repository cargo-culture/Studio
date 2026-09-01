import json
import pytest
from studio_runner.config import load_config
from studio_runner.util import StudioError

def test_template_config_loads(tmp_path):
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(json.dumps({"studio":{"canonical_branch":"main"},"review":{"max_builder_reviewer_rounds":2}}))
    c = load_config(tmp_path)
    assert c.canonical_branch == "main"
    assert c.max_review_rounds == 2
    assert c.builder_policy.permission_mode == "dontAsk"
    assert c.builder_policy.restricted_to_worktree is True
    assert "Bash(python -m pytest)" in c.builder_policy.allowed_tools
    assert "Bash" not in c.builder_policy.allowed_tools


@pytest.mark.parametrize(
    "permissions",
    [
        {"mode": "bypassPermissions"},
        {"mode": "acceptEdits"},
        {"restricted_to_worktree": False},
        {"tools": ["Read", "Glob", "Grep", "Edit", "Write", "Bash", "PowerShell"]},
        {"allow": ["Read", "Glob", "Grep", "Edit", "Write", "Bash"]},
        {"allow": ["Read", "Glob", "Grep", "Edit", "Write", "Bash(pytest *)"]},
    ],
)
def test_builder_policy_rejects_broader_permissions(tmp_path, permissions):
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(
        json.dumps({"agents": {"builder": {"permissions": permissions}}})
    )

    with pytest.raises(StudioError):
        load_config(tmp_path).builder_policy
