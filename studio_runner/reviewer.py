from __future__ import annotations
from pathlib import Path
import json, os, urllib.request, urllib.error
from .budget import Budget
from .util import run, StudioError

REVIEW_SYSTEM = """You are the Independent Staff Engineer in a three-agent software studio. You are reviewing another engineer's implementation. Do not assume it is correct. Check it against requirements, architecture, diff and tests. Do not redesign the product unless necessary to satisfy the requirements. Avoid stylistic nitpicks.
Return findings grouped exactly under BLOCKER, MAJOR, MINOR, OPTIONAL. Each finding must include location, claim, evidence/reason, and smallest sensible correction. End with VERDICT: PASS or VERDICT: CHANGES_REQUIRED."""


def build_review_packet(root: Path, issue, base_branch: str, builder_summary: str) -> str:
    diff = run(["git", "diff", f"{base_branch}...HEAD", "--"], cwd=root).stdout
    stat = run(["git", "diff", "--stat", f"{base_branch}...HEAD"], cwd=root).stdout
    state = (root / ".studio" / "state.md").read_text(encoding="utf-8") if (root / ".studio" / "state.md").exists() else ""
    return f"""TASK
#{issue.number} {issue.title}

REQUIREMENTS
{issue.body}

STUDIO STATE
{state}

BUILDER SUMMARY
{builder_summary}

DIFF STAT
{stat}

DIFF
{diff}
"""


def estimate_credits(packet: str, expected_output_chars=12000) -> float:
    # Conservative local estimate only. Venice server-side billing remains authoritative.
    # Approx 4 chars/token. Default GLM prices encoded from Studio policy assumptions.
    in_k = len(packet) / 4 / 1000
    out_k = expected_output_chars / 4 / 1000
    return in_k * 0.14 + out_k * 0.44


def review(root: Path, config, packet: str, budget_root: Path | None = None) -> str:
    key = os.getenv("VENICE_API_KEY")
    if not key:
        raise StudioError("VENICE_API_KEY_NOT_CONFIGURED")
    budget_base = budget_root or root
    budget = Budget(budget_base / ".studio" / "runtime" / "venice-budget.json", config.venice_credit_ceiling)
    est = estimate_credits(packet)
    if not budget.can_spend(est):
        raise StudioError("VENICE_CREDIT_CEILING_REACHED")
    body = {
        "model": config.reviewer_model,
        "messages": [
            {"role": "system", "content": REVIEW_SYSTEM},
            {"role": "user", "content": packet},
        ],
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        "https://api.venice.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise StudioError(f"Venice review failed: HTTP {e.code} {e.read().decode(errors='ignore')[:1000]}")
    text = data["choices"][0]["message"]["content"]
    budget.record(est)
    return text
