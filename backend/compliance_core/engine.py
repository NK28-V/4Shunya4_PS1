from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .models import Violation
from .result import EngineResult
from .utils import unique_in_order
from .rules import DEFAULT_RULES


class Rule(Protocol):
    framework: str

    def evaluate(self, config: dict[str, Any]) -> list[Violation]: ...


@dataclass(slots=True)
class ComplianceEngine:
    rules: list[Rule]

    @classmethod
    def default(cls) -> "ComplianceEngine":
        return cls(rules=list(DEFAULT_RULES))

    def evaluate(self, config: dict[str, Any]) -> EngineResult:
        violations: list[Violation] = []
        frameworks: list[str] = []

        for rule in self.rules:
            frameworks.append(rule.framework)
            violations.extend(rule.evaluate(config))

        return EngineResult(
            violations=violations,
            frameworks_checked=unique_in_order(frameworks),
        )


def evaluate_config(config: dict[str, Any]) -> EngineResult:
    """
    Convenience function for the common case: run the default ruleset.
    """
    return ComplianceEngine.default().evaluate(config)

