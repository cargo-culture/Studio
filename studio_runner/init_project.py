from __future__ import annotations
from pathlib import Path
import shutil
from .util import StudioError
from .github import ensure_labels


def copy_template(source_root: Path, target: Path, force=False):
    template = source_root / "studio_runner" / "template"
    if not template.exists():
        raise StudioError(f"template directory missing: {template}")
    for src in template.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(template)
        dst = target / rel
        if dst.exists() and not force:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def init_project(source_root: Path, target: Path, force=False):
    if not (target / ".git").exists():
        raise StudioError(f"target is not a git repository: {target}")
    copy_template(source_root, target, force)
    ensure_labels(target)
    return target
