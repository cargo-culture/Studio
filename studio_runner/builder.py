from __future__ import annotations
from pathlib import Path
import os
from .util import run, StudioError

BUILDER_PROMPT = """You are the Builder / Production Lead for Atelier3A (A3A), a three-agent software studio.
Read and obey AGENTS.md and .studio/state.md before editing.

ISSUE #{number}: {title}

{body}

You are expected to IMPLEMENT the requested change in the current repository worktree, not merely describe or suggest it. Use the available repository editing tools to create or modify files as required by the accepted scope.
Preserve human product intent and existing architecture. Use repository evidence and tests rather than assumptions. If a material product or architecture decision is unresolved, stop and end with PRINCIPAL_NEEDED and explain exactly what decision is required.
Run the relevant tests/build/lint/type checks available for the affected subsystem.
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

REVIEW FINDINGS:
{review}

Return SUMMARY, CORRECTIONS, REJECTED_FINDINGS, TESTS, STATUS.
"""


def _safe_env():
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    return env


def run_builder(worktree: Path, issue, correction_review: str | None = None) -> str:
    prompt = CORRECTION_PROMPT.format(review=correction_review) if correction_review else BUILDER_PROMPT.format(number=issue.number, title=issue.title, body=issue.body)
    p = run(["claude", "-p", "--permission-mode", "acceptEdits", prompt], cwd=worktree, check=False, env=_safe_env())
    text = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    low = text.lower()
    if "usage limit" in low or "rate limit" in low:
        raise StudioError("BUILDER_QUOTA_EXHAUSTED")
    if p.returncode != 0:
        raise StudioError(f"builder failed ({p.returncode}): {text[-2000:]}")
    return text.strip()
