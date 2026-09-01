from __future__ import annotations
from pathlib import Path

def write_state(root: Path, *, objective: str, active: str, builder: str, review: str, blockers: str, next_: str):
    text = f"""# Studio State\n\nCURRENT OBJECTIVE\n{objective}\n\nACTIVE\n{active}\n\nBUILDER\n{builder}\n\nREVIEW\n{review}\n\nBLOCKERS\n{blockers}\n\nNEXT\n{next_}\n"""
    runtime = root / ".studio" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "state.md").write_text(text, encoding="utf-8")
