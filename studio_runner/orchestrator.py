from __future__ import annotations
from pathlib import Path
from .config import load_config
from . import github
from .builder import run_builder
from .reviewer import build_review_packet, review
from .state import write_state
from .util import run, StudioError


def _make_worktree(root: Path, branch: str, base: str, issue_number: int) -> Path:
    parent = root.parent / ".studio-worktrees"
    parent.mkdir(exist_ok=True)
    wt = parent / f"{root.name}-{issue_number}"
    if wt.exists():
        run(["git", "worktree", "remove", "--force", str(wt)], cwd=root, check=False)
    run(["git", "fetch", "origin", base], cwd=root)
    exists = run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=root, check=False).returncode == 0
    if exists:
        run(["git", "worktree", "add", str(wt), branch], cwd=root)
    else:
        run(["git", "worktree", "add", "-b", branch, str(wt), f"origin/{base}"], cwd=root)
    return wt


def _commit_push(worktree: Path, branch: str, message: str):
    run(["git", "add", "-A"], cwd=worktree)
    changed = run(["git", "diff", "--cached", "--quiet"], cwd=worktree, check=False).returncode != 0
    if changed:
        run(["git", "commit", "-m", message], cwd=worktree)
    run(["git", "push", "-u", "origin", branch], cwd=worktree)


def _ensure_pr(worktree: Path, issue, base: str, branch: str) -> str:
    p = run(["gh", "pr", "list", "--head", branch, "--json", "url", "-q", ".[0].url"], cwd=worktree)
    if p.stdout.strip():
        return p.stdout.strip()
    body = f"Implements #{issue.number}.\n\nManaged by Atelier3A (A3A). Human approval required before merge."
    p = run(["gh", "pr", "create", "--base", base, "--head", branch, "--title", issue.title, "--body", body], cwd=worktree)
    return p.stdout.strip()


def process_issue(root: Path, number: int) -> dict:
    cfg = load_config(root)
    issue = github.issue(root, number)
    branch = cfg.branch_pattern.format(issue_number=issue.number, slug=github.slugify(issue.title))
    github.set_state(root, number, "studio:building")
    write_state(root, objective=issue.title, active=f"#{number}", builder=f"Claude — {branch}", review="Pending", blockers="None", next_="Builder implementation")
    wt = _make_worktree(root, branch, cfg.canonical_branch, issue.number)
    try:
        summary = run_builder(wt, issue)
        if "PRINCIPAL_NEEDED" in summary:
            github.set_state(root, number, "studio:principal-needed")
            github.add_comment(root, number, "PRINCIPAL_NEEDED\n\n" + summary)
            return {"status": "principal-needed", "summary": summary}
        _commit_push(wt, branch, f"studio: implement #{number} {issue.title}")
        pr = _ensure_pr(wt, issue, cfg.canonical_branch, branch)
        github.set_state(root, number, "studio:reviewing")
        review_text = None
        if cfg.reviewer_enabled:
            try:
                packet = build_review_packet(wt, issue, cfg.canonical_branch, summary)
                review_text = review(wt, cfg, packet, budget_root=root)
                github.add_comment(root, number, f"INDEPENDENT REVIEW\n\n{review_text}")
            except StudioError as e:
                if str(e) in {"VENICE_CREDIT_CEILING_REACHED", "VENICE_API_KEY_NOT_CONFIGURED"}:
                    github.set_state(root, number, "studio:principal-needed")
                    github.add_comment(root, number, f"PRINCIPAL_NEEDED\n\nIndependent automated review unavailable: {e}")
                    return {"status": "principal-needed", "pr": pr, "reason": str(e)}
                raise
        rounds = 0
        while review_text and "VERDICT: CHANGES_REQUIRED" in review_text and rounds < cfg.max_review_rounds:
            rounds += 1
            github.set_state(root, number, "studio:correcting")
            correction = run_builder(wt, issue, correction_review=review_text)
            _commit_push(wt, branch, f"studio: address review #{number} round {rounds}")
            github.set_state(root, number, "studio:reviewing")
            packet = build_review_packet(wt, issue, cfg.canonical_branch, correction)
            review_text = review(wt, cfg, packet, budget_root=root)
            github.add_comment(root, number, f"INDEPENDENT REVIEW ROUND {rounds+1}\n\n{review_text}")
        if review_text and "VERDICT: CHANGES_REQUIRED" in review_text:
            github.set_state(root, number, "studio:principal-needed")
            return {"status": "principal-needed", "pr": pr, "reason": "review rounds exhausted"}
        github.set_state(root, number, "studio:human-review")
        write_state(root, objective=issue.title, active=f"#{number}", builder=f"Complete — {branch}", review="Independent review complete", blockers="None", next_="Human final build review")
        github.add_comment(root, number, f"READY FOR HUMAN REVIEW\n\nBuilder summary:\n{summary}\n\nPR: {pr}\n\nReviewer:\n{review_text or 'Principal review required'}")
        return {"status": "human-review", "pr": pr, "summary": summary, "review": review_text}
    except StudioError as e:
        github.set_state(root, number, "studio:blocked")
        github.add_comment(root, number, f"A3A BLOCKED\n\n{e}")
        write_state(root, objective=issue.title, active=f"#{number}", builder="Blocked", review="Not complete", blockers=str(e), next_="Resolve blocker")
        raise
    finally:
        run(["git", "worktree", "remove", "--force", str(wt)], cwd=root, check=False)
