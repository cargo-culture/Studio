from __future__ import annotations
import json, os, shlex, subprocess
from pathlib import Path

class StudioError(RuntimeError):
    pass

def run(cmd, cwd=None, check=True, capture=True, env=None):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    merged = os.environ.copy()
    if env:
        merged.update(env)
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture, env=merged)
    if check and p.returncode != 0:
        raise StudioError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr.strip()}")
    return p

def gh_json(args, cwd=None):
    p = run(["gh", *args], cwd=cwd)
    return json.loads(p.stdout or "null")

def repo_root(cwd=None) -> Path:
    p = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(p.stdout.strip())
