"""
Centralized scoring weights for the Vibe-to-Value production readiness score.

Tune these constants to adjust deduction amounts and thresholds without
changing the scoring algorithm implementation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Base score (starting value before any deductions)
# ---------------------------------------------------------------------------
BASE_SCORE: int = 100

# ---------------------------------------------------------------------------
# Deduction weights (points subtracted per occurrence or per condition)
# ---------------------------------------------------------------------------

# Per instance of hardcoded secret or exposed API key
DEDUCT_PER_SECRET_OR_API_KEY: int = 35

# Per identified hallucinated package dependency
DEDUCT_PER_HALLUCINATED_DEPENDENCY: int = 25

# One-time deduction when SOC 2 Multi-Factor Authentication (MFA) check fails
DEDUCT_SOC2_MFA_FAILED: int = 15

# One-time deduction when GDPR explicit consent mechanisms are missing
# or unhashed PII sinks are present
DEDUCT_GDPR_OR_UNHASHED_PII: int = 15

# One-time deduction when overall code coverage is below the coverage threshold
DEDUCT_LOW_COVERAGE: int = 5

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Code coverage percentage below which DEDUCT_LOW_COVERAGE is applied
COVERAGE_THRESHOLD_PERCENT: float = 75.0

# Minimum score (inclusive) above which deployment is allowed.
# If final score < DEPLOYMENT_BLOCK_THRESHOLD, DEPLOYMENT_BLOCKED is set to True.
DEPLOYMENT_BLOCK_THRESHOLD: int = 60

# Floor: computed score is never reported below this value
SCORE_FLOOR: int = 0
