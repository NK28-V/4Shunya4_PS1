from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import Violation
from ..utils import MISSING, get_in


@dataclass(frozen=True, slots=True)
class Soc2MfaEnabledRule:
    framework: str = "SOC2"

    def evaluate(self, config: dict[str, Any]) -> list[Violation]:
        path = "logical_access.mfa_enabled"
        value = get_in(config, path, default=MISSING)
        if value is True:
            return []

        return [
            Violation(
                id="SOC2.MFA.NOT_ENABLED",
                framework=self.framework,
                control="Logical Access",
                severity="high",
                message="MFA is not enabled (or is missing) for user access.",
                path=path,
                evidence={"value": None if value is MISSING else value},
            )
        ]


@dataclass(frozen=True, slots=True)
class Soc2RbacPresentRule:
    framework: str = "SOC2"

    def evaluate(self, config: dict[str, Any]) -> list[Violation]:
        path = "logical_access.rbac_present"
        value = get_in(config, path, default=MISSING)
        if value is True:
            return []

        return [
            Violation(
                id="SOC2.RBAC.NOT_PRESENT",
                framework=self.framework,
                control="Logical Access",
                severity="high",
                message="RBAC is not present (or is missing).",
                path=path,
                evidence={"value": None if value is MISSING else value},
            )
        ]

