from __future__ import annotations

import json
from dataclasses import dataclass, field

from .models import Violation


@dataclass(slots=True)
class EngineResult:
    violations: list[Violation] = field(default_factory=list)
    frameworks_checked: list[str] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def to_dict(self) -> dict:
        return {
            "violations": [v.to_dict() for v in self.violations],
            "violation_count": self.violation_count,
            "frameworks_checked": list(self.frameworks_checked),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

