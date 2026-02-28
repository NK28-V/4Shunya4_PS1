from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import Violation
from ..utils import MISSING, get_in


@dataclass(frozen=True, slots=True)
class GdprEncryptionFlagsRule:
    """
    Detect missing encryption flags for PII.

    Supported config fields (either approach is acceptable):
    - data_protection.pii_encrypted (single boolean)
    - data_protection.encryption_at_rest + data_protection.encryption_in_transit (two booleans)
    """

    framework: str = "GDPR"

    def evaluate(self, config: dict[str, Any]) -> list[Violation]:
        single_flag_path = "data_protection.pii_encrypted"
        single_flag = get_in(config, single_flag_path, default=MISSING)

        at_rest_path = "data_protection.encryption_at_rest"
        in_transit_path = "data_protection.encryption_in_transit"
        at_rest = get_in(config, at_rest_path, default=MISSING)
        in_transit = get_in(config, in_transit_path, default=MISSING)

        if single_flag is not MISSING:
            if single_flag is True:
                return []
            return [
                Violation(
                    id="GDPR.PII.ENCRYPTION.NOT_ENABLED",
                    framework=self.framework,
                    control="Data Protection",
                    severity="high",
                    message="PII encryption flag is not enabled.",
                    path=single_flag_path,
                    evidence={"value": single_flag},
                )
            ]

        # No single flag; accept the pair if both are present and true
        if at_rest is MISSING and in_transit is MISSING:
            return [
                Violation(
                    id="GDPR.PII.ENCRYPTION.FLAGS_MISSING",
                    framework=self.framework,
                    control="Data Protection",
                    severity="high",
                    message="Missing encryption flags for PII (expected pii_encrypted or encryption_at_rest/encryption_in_transit).",
                    path="data_protection",
                    evidence={},
                )
            ]

        if at_rest is True and in_transit is True:
            return []

        return [
            Violation(
                id="GDPR.PII.ENCRYPTION.NOT_ENABLED",
                framework=self.framework,
                control="Data Protection",
                severity="high",
                message="Encryption is not fully enabled for PII (at rest and in transit).",
                path="data_protection",
                evidence={
                    "encryption_at_rest": None if at_rest is MISSING else at_rest,
                    "encryption_in_transit": None if in_transit is MISSING else in_transit,
                },
            )
        ]

