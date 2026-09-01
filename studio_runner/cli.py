from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
from .util import repo_root, StudioError, run
from .init_project import init_project
from .orchestrator import process_issue
from .github import queued_issues, ensure_labels


def parser():
    p = argparse.ArgumentParser(prog="a3a", description="Atelier3A (A3A) orchestrator")
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("init", help="install the A3A template into a project repo")
    q.add_argument("path", nargs="?", default=".")
    q.add_argument("--force", action="store_true")
    q = sub.add_parser("process", help="process one GitHub issue")
    q.add_argument("issue", type=int)
    q = sub.add_parser("run", help="poll queued issues")
    q.add_argument("--once", action="store_true")
    q.add_argument("--interval", type=int, default=60)
    sub.add_parser("labels", help="create/update A3A workflow labels")
    sub.add_parser("setup", help="one-step local A3A setup/check")
    sub.add_parser("doctor", help="check local prerequisites")
    return p


def doctor():
    checks = {}
    for name, cmd in {"git": ["git", "--version"], "gh": ["gh", "--version"], "claude": ["claude", "--version"]}.items():
        try:
            x = run(cmd, check=False)
            checks[name] = x.returncode == 0
        except FileNotFoundError:
            checks[name] = False
    checks["anthropic_api_key_absent"] = not bool(__import__("os").environ.get("ANTHROPIC_API_KEY"))
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.cmd == "doctor":
            return doctor()
        root = repo_root()
        if args.cmd == "init":
            source = Path(__file__).resolve().parents[1]
            target = Path(args.path).resolve()
            init_project(source, target, args.force)
            print(f"Atelier3A installed in {target}")
            return 0
        if args.cmd == "labels":
            ensure_labels(root)
            print("A3A labels ready")
            return 0
        if args.cmd == "setup":
            code = doctor()
            if code != 0:
                print("Fix the failed prerequisites above, then rerun ./a3a setup", file=sys.stderr)
                return code
            ensure_labels(root)
            print("Atelier3A ready. Start with: ./a3a run")
            return 0
        if args.cmd == "process":
            print(json.dumps(process_issue(root, args.issue), indent=2))
            return 0
        if args.cmd == "run":
            while True:
                q = queued_issues(root)
                if q:
                    for issue in q:
                        try:
                            print(json.dumps(process_issue(root, issue.number), indent=2))
                        except StudioError as e:
                            print(f"Issue #{issue.number}: {e}", file=sys.stderr)
                if args.once:
                    return 0
                time.sleep(args.interval)
    except StudioError as e:
        print(f"a3a: {e}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
