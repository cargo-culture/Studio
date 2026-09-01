from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from .util import StudioError

@dataclass
class Config:
    data: dict
    path: Path

    @property
    def canonical_branch(self):
        return self.data.get("studio", {}).get("canonical_branch", "main")

    @property
    def branch_pattern(self):
        return self.data.get("github", {}).get("branch_pattern", "studio/{issue_number}-{slug}")

    @property
    def reviewer_enabled(self):
        return bool(self.data.get("agents", {}).get("reviewer", {}).get("enabled", True))

    @property
    def reviewer_model(self):
        return self.data.get("agents", {}).get("reviewer", {}).get("model_policy", {}).get("default", "zai-org-glm-5-2")

    @property
    def venice_credit_ceiling(self):
        return float(self.data.get("agents", {}).get("reviewer", {}).get("cost_control", {}).get("monthly_venice_credit_ceiling", 100))

    @property
    def max_review_rounds(self):
        return int(self.data.get("review", {}).get("max_builder_reviewer_rounds", 2))

def load_config(root: Path) -> Config:
    path = root / ".studio" / "studio.yaml"
    if not path.exists():
        raise StudioError(f"missing config: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise StudioError(f"{path} must use JSON-compatible YAML syntax: {e}") from e
    return Config(data or {}, path)
