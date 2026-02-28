from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from ..ast_scanner import PiiFinding, PiiScanResult
from ..models import Violation


_PII_GDPR_MAPPING: dict[str, dict[str, str]] = {
    # High‑risk identifiers -> Article 32
    "ssn": {
        "article": "32",
        "control": "Security of Processing",
        "severity": "high",
        "id": "GDPR.ART32.PII.HIGH_RISK_IDENTIFIER",
    },
    "password": {
        "article": "32",
        "control": "Security of Processing",
        "severity": "high",
        "id": "GDPR.ART32.PII.HIGH_RISK_IDENTIFIER",
    },
    # Contact details -> Article 5 (data minimization)
    "email": {
        "article": "5",
        "control": "Data Minimization",
        "severity": "medium",
        "id": "GDPR.ART5.PII.CONTACT_DATA",
    },
    "phone": {
        "article": "5",
        "control": "Data Minimization",
        "severity": "medium",
        "id": "GDPR.ART5.PII.CONTACT_DATA",
    },
}

_DEFAULT_MAPPING: dict[str, str] = {
    "article": "5",
    "control": "Data Protection",
    "severity": "medium",
    "id": "GDPR.PII.GENERIC",
}


@dataclass(frozen=True, slots=True)
class PiiAdapter:
    """
    Transform AST-based PII findings into GDPR violations compatible with the scoring engine.

    The mapping is deterministic:
    - ssn/password -> GDPR Article 32, high severity
    - email/phone  -> GDPR Article 5, medium severity

    Evidence always includes: filename, lineno, and context.
    """

    framework: str = "GDPR"

    def finding_to_violation(self, finding: PiiFinding) -> Violation:
        """
        Convert a single PiiFinding into a Violation.
        """
        meta = _PII_GDPR_MAPPING.get(finding.pii_type.lower(), _DEFAULT_MAPPING)

        article = meta["article"]
        control = meta["control"]
        severity = meta["severity"]
        violation_id = meta["id"]

        control_label = f"{control} (Art. {article})"
        message = (
            f"Potential {finding.pii_type} PII detected in source code "
            f"(GDPR Article {article}: {control})."
        )

        evidence = {
            "filename": finding.filename,
            "lineno": finding.lineno,
            "col_offset": finding.col_offset,
            "context": finding.context,
            "variable_name": finding.name,
            "pii_type": finding.pii_type,
            "severity": finding.severity,
        }

        return Violation(
            id=violation_id,
            framework=self.framework,
            control=control_label,
            severity=severity,
            message=message,
            path=finding.filename,
            evidence=evidence,
        )

    def findings_to_violations(self, findings: Iterable[PiiFinding]) -> list[Violation]:
        """
        Convert an iterable of PiiFinding objects into a list of Violation objects.
        """
        return [self.finding_to_violation(f) for f in findings]

    def scan_result_to_violations(self, scan_result: PiiScanResult) -> list[Violation]:
        """
        Convenience helper to adapt an entire PiiScanResult.
        """
        return self.findings_to_violations(scan_result.findings)

