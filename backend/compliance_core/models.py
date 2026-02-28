from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Violation:
    """
    A single compliance finding. Keep this structure stable because it's part of the JSON output.
    """

    id: str
    framework: str  # e.g. "SOC2", "GDPR"
    control: str  # high-level area, e.g. "Logical Access"
    severity: str  # e.g. "low" | "medium" | "high"
    message: str
    path: str = ""  # dotted path into the config, e.g. "logical_access.mfa_enabled"
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

