"""
Vibe-to-Value production readiness scoring service.

Consumes integrated JSON output from:
  - prompt_injection_scanner.py (prompt-injection results; not used in current
    score formula but payload can be passed through)
  - ast_scanner.py (PII findings → GDPR/unhashed PII sink signals)
  - soc2.py (SOC 2 violations → MFA check)

Integrated report schema (expected keys, all optional):
  - secrets_or_api_keys: int or list — count of hardcoded secrets / exposed API keys
  - hallucinated_dependencies: int or list — count of hallucinated packages
  - soc2_mfa_failed: bool — True if MFA check failed; OR
  - soc2_violations: list of {id, ...} — presence of id "SOC2.MFA.NOT_ENABLED" = MFA failed
  - gdpr_consent_missing_or_unhashed_pii: bool — True if missing consent or unhashed PII; OR
  - pii_scan_results: list/dict of ast_scanner-style results — findings used as unhashed PII
  - code_coverage_percent: float | None — overall coverage; < 75 triggers deduction

All scoring weights and thresholds are in constants.py for easy tuning.
"""

from __future__ import annotations

import json
from typing import Any

from constants import (
    BASE_SCORE,
    COVERAGE_THRESHOLD_PERCENT,
    DEDUCT_GDPR_OR_UNHASHED_PII,
    DEDUCT_LOW_COVERAGE,
    DEDUCT_PER_HALLUCINATED_DEPENDENCY,
    DEDUCT_PER_SECRET_OR_API_KEY,
    DEDUCT_SOC2_MFA_FAILED,
    DEPLOYMENT_BLOCK_THRESHOLD,
    SCORE_FLOOR,
)

# Compliance core types (for integration with vibe_audit_engine / reporting)
try:
    from backend.compliance_core.rules.soc2 import Soc2MfaEnabledRule
    from backend.compliance_core.adapters.pii_adapter import PiiAdapter
except ImportError:
    Soc2MfaEnabledRule = None  # type: ignore[misc, assignment]
    PiiAdapter = None  # type: ignore[misc, assignment]

# Violation id that indicates failed MFA check (from soc2.Soc2MfaEnabledRule)
SOC2_MFA_VIOLATION_ID = "SOC2.MFA.NOT_ENABLED"


def _count(x: int | list[Any] | None) -> int:
    """Return count from int or length of list; None/absent → 0."""
    if x is None:
        return 0
    if isinstance(x, list):
        return len(x)
    if isinstance(x, int) and x >= 0:
        return x
    return 0


def _soc2_mfa_failed(report: dict[str, Any]) -> bool:
    """True if SOC 2 MFA check failed (MFA not enabled)."""
    if report.get("soc2_mfa_failed") is True:
        return True
    violations = report.get("soc2_violations")
    if not isinstance(violations, list):
        return False
    for v in violations:
        if isinstance(v, dict) and v.get("id") == SOC2_MFA_VIOLATION_ID:
            return True
        if getattr(v, "id", None) == SOC2_MFA_VIOLATION_ID:
            return True
    return False


def _gdpr_or_unhashed_pii(report: dict[str, Any]) -> bool:
    """True if GDPR explicit consent is missing or unhashed PII sinks present."""
    if report.get("gdpr_consent_missing_or_unhashed_pii") is True:
        return True
    # Derive from ast_scanner-style PII results: presence of PII findings
    # can be treated as unhashed PII sinks when no consent/hashing is indicated
    pii_results = report.get("pii_scan_results")
    if isinstance(pii_results, list):
        for r in pii_results:
            if isinstance(r, dict) and _count(r.get("findings", 0)) > 0:
                return True
            if hasattr(r, "findings") and len(getattr(r, "findings", [])) > 0:
                return True
    if isinstance(pii_results, dict) and _count(pii_results.get("findings", 0)) > 0:
        return True
    return False


def _coverage_below_threshold(report: dict[str, Any]) -> bool:
    """True if code_coverage_percent is present and strictly below threshold."""
    cov = report.get("code_coverage_percent")
    if cov is None:
        return False
    try:
        return float(cov) < COVERAGE_THRESHOLD_PERCENT
    except (TypeError, ValueError):
        return False


def compute_score(report: dict[str, Any]) -> int:
    """
    Compute the Vibe-to-Value production readiness score (deterministic).

    Deductions (from constants.py):
      - DEDUCT_PER_SECRET_OR_API_KEY per hardcoded secret / exposed API key
      - DEDUCT_PER_HALLUCINATED_DEPENDENCY per hallucinated dependency
      - DEDUCT_SOC2_MFA_FAILED if SOC 2 MFA check failed
      - DEDUCT_GDPR_OR_UNHASHED_PII if GDPR consent missing or unhashed PII
      - DEDUCT_LOW_COVERAGE if code coverage < COVERAGE_THRESHOLD_PERCENT

    Score is floored at SCORE_FLOOR (0).
    """
    score = BASE_SCORE

    n_secrets = _count(report.get("secrets_or_api_keys"))
    score -= n_secrets * DEDUCT_PER_SECRET_OR_API_KEY

    n_hallucinated = _count(report.get("hallucinated_dependencies"))
    score -= n_hallucinated * DEDUCT_PER_HALLUCINATED_DEPENDENCY

    if _soc2_mfa_failed(report):
        score -= DEDUCT_SOC2_MFA_FAILED

    if _gdpr_or_unhashed_pii(report):
        score -= DEDUCT_GDPR_OR_UNHASHED_PII

    if _coverage_below_threshold(report):
        score -= DEDUCT_LOW_COVERAGE

    return max(SCORE_FLOOR, score)


def build_result_payload(
    report: dict[str, Any],
    *,
    include_report: bool = True,
) -> dict[str, Any]:
    """
    Build the final JSON response payload with score and DEPLOYMENT_BLOCKED.

    If the computed score is strictly less than DEPLOYMENT_BLOCK_THRESHOLD (60),
    appends DEPLOYMENT_BLOCKED: true to the payload.
    """
    score = compute_score(report)
    payload: dict[str, Any] = {
        "vibe_to_value_score": score,
        "score_floor_applied": score == SCORE_FLOOR and score < BASE_SCORE,
    }
    if score < DEPLOYMENT_BLOCK_THRESHOLD:
        payload["DEPLOYMENT_BLOCKED"] = True
    if include_report:
        payload["integrated_report"] = report
    return payload


def score_and_serialize(report: dict[str, Any], *, indent: int | None = 2) -> str:
    """Compute score, build payload, and return JSON string."""
    payload = build_result_payload(report, include_report=True)
    return json.dumps(payload, indent=indent)


def main() -> None:
    """CLI: read integrated report JSON from stdin or first arg; print scored payload."""
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            report = json.load(f)
    else:
        report = json.load(sys.stdin)
    print(score_and_serialize(report))


if __name__ == "__main__":
    main()
