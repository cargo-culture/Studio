from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
from .util import gh_json, run, StudioError

STATE_LABELS = [
    "studio:queued", "studio:building", "studio:reviewing", "studio:correcting",
    "studio:principal-needed", "studio:human-review", "studio:approved",
    "studio:blocked", "studio:held"
]
RISK_LABELS = ["risk:low", "risk:normal", "risk:high"]

@dataclass
class Issue:
    number: int
    title: str
    body: str
    labels: list[str]
    url: str


def repo_name(root: Path) -> str:
    p = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], cwd=root)
    return p.stdout.strip()


def queued_issues(root: Path) -> list[Issue]:
    data = gh_json(["issue", "list", "--label", "studio:queued", "--state", "open", "--limit", "50", "--json", "number,title,body,labels,url"], cwd=root)
    return [Issue(x["number"], x["title"], x.get("body") or "", [l["name"] for l in x.get("labels", [])], x["url"]) for x in data]


def issue(root: Path, number: int) -> Issue:
    x = gh_json(["issue", "view", str(number), "--json", "number,title,body,labels,url"], cwd=root)
    return Issue(x["number"], x["title"], x.get("body") or "", [l["name"] for l in x.get("labels", [])], x["url"])


def set_state(root: Path, number: int, state: str):
    if state not in STATE_LABELS:
        raise StudioError(f"unknown state label {state}")
    cur = issue(root, number)
    for label in cur.labels:
        if label in STATE_LABELS and label != state:
            run(["gh", "issue", "edit", str(number), "--remove-label", label], cwd=root, check=False)
    if state not in cur.labels:
        run(["gh", "issue", "edit", str(number), "--add-label", state], cwd=root)


def add_comment(root: Path, number: int, text: str):
    run(["gh", "issue", "comment", str(number), "--body", text], cwd=root)


def ensure_labels(root: Path):
    for label in STATE_LABELS + RISK_LABELS:
        run(["gh", "label", "create", label, "--force", "--description", "Atelier3A (A3A) workflow label"], cwd=root)


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:48] or "task"
