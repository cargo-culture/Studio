from __future__ import annotations
from pathlib import Path
import os
from .config import BuilderPolicy
from .util import run, StudioError

BUILDER_PROMPT = """You are the Builder / Production Lead for Atelier3A (A3A), a three-agent software studio.
Read and obey AGENTS.md and .studio/state.md before editing.

ISSUE #{number}: {title}

{body}

You are expected to IMPLEMENT the requested change in the current repository worktree, not merely describe or suggest it. Use the available repository editing tools to create or modify files as required by the accepted scope.
Preserve human product intent and existing architecture. Use repository evidence and tests rather than assumptions. If a material product or architecture decision is unresolved, stop and end with PRINCIPAL_NEEDED and explain exactly what decision is required.
Run the relevant tests/build/lint/type checks available for the affected subsystem.
Use only an exact repository verification entry point approved by A3A, without extra flags, paths, redirections, wrappers, or chained commands. Use the file tools—not shell commands—to inspect the repository.
Do not merge to main.

At completion return exactly these sections:
SUMMARY
FILES
TESTS
ASSUMPTIONS
RISKS
STATUS
"""

CORRECTION_PROMPT = """You are the canonical Builder for Atelier3A (A3A). Review the independent findings below against the code and requirements. Do not blindly accept them. Verify each claim, correct valid BLOCKER/MAJOR findings by actually editing the current repository worktree, run relevant tests, and explain any rejected finding with evidence.
Use only an exact repository verification entry point approved by A3A, without extra flags, paths, redirections, wrappers, or chained commands. Use the file tools—not shell commands—to inspect the repository.

REVIEW FINDINGS:
{review}

Return SUMMARY, CORRECTIONS, REJECTED_FINDINGS, TESTS, STATUS.
"""


def _safe_env(policy: BuilderPolicy):
    env = os.environ.copy()
    forbidden = {name.upper() for name in policy.forbidden_environment_variables}
    for name in tuple(env):
        if name.upper() in forbidden:
            env.pop(name, None)
    return env


def _claude_command(policy: BuilderPolicy, prompt: str) -> list[str]:
    return [
        "claude",
        "-p",
        "--restricted",
        "--permission-mode",
        policy.permission_mode,
        "--tools",
        ",".join(policy.tools),
        "--allowedTools",
        ",".join(policy.allowed_tools),
        "--disallowedTools",
        ",".join(policy.denied_tools),
        "--strict-mcp-config",
        "--no-chrome",
        "--no-session-persistence",
        prompt,
    ]


def run_builder(worktree: Path, issue, policy: BuilderPolicy, correction_review: str | None = None) -> str:
    prompt = CORRECTION_PROMPT.format(review=correction_review) if correction_review else BUILDER_PROMPT.format(number=issue.number, title=issue.title, body=issue.body)
    p = run(_claude_command(policy, prompt), cwd=worktree, check=False, env=_safe_env(policy))
    text = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    low = text.lower()
    if "usage limit" in low or "rate limit" in low:
        raise StudioError("BUILDER_QUOTA_EXHAUSTED")
    if p.returncode != 0:
        raise StudioError(f"builder failed ({p.returncode}): {text[-2000:]}")
    return text.strip()
