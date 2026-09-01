from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json

@dataclass
class Budget:
    path: Path
    ceiling: float

    def _month(self):
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def load(self):
        if not self.path.exists():
            return {"month": self._month(), "credits_estimated": 0.0}
        try:
            x = json.loads(self.path.read_text())
        except Exception:
            x = {}
        if x.get("month") != self._month():
            x = {"month": self._month(), "credits_estimated": 0.0}
        return x

    def can_spend(self, estimated_credits: float) -> bool:
        x = self.load()
        return x["credits_estimated"] + estimated_credits <= self.ceiling

    def record(self, estimated_credits: float):
        x = self.load()
        x["credits_estimated"] += estimated_credits
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(x, indent=2) + "\n")
