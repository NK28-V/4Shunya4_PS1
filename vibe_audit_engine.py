"""
Vibe Audit Engine — Master orchestration script.

Runs prompt-injection scan, compliance engine (SOC 2 / GDPR), and AST PII scan
on a target Python file; aggregates results into an Integrated Report and
computes the Vibe-to-Value production readiness score.
"""

from __future__ import annotations

import json
import sys
import re   
from pathlib import Path

# Ensure project root is on path for backend and root-level modules
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from prompt_injection_scanner import PromptScanner

from backend.compliance_core.engine import ComplianceEngine
from backend.compliance_core.ast_scanner import scan_python_file
from backend.compliance_core.adapters.pii_adapter import PiiAdapter

from scoring_algorithm import build_result_payload

# Regex to detect hardcoded secrets / API keys in source (for integrated_report)
_SECRET_PATTERN = re.compile(
    r"(?:SECRET|API_KEY|TOKEN|PASSWORD)\s*=\s*[\'\"][^\'\"]+[\'\"]",
    re.IGNORECASE,
)


def _prompt_result_to_dict(result) -> dict:
    """Convert PromptScanner ScanResult to a JSON-serializable dict."""
    return {
        "is_injection": result.is_injection,
        "overall_score": result.overall_score,
        "layer1_score": result.layer1_score,
        "layer2_score": result.layer2_score,
        "layer3_score": result.layer3_score,
        "layer3_type": result.layer3_type,
        "layer3_explanation": result.layer3_explanation,
        "errors": getattr(result, "errors", []),
    }


def run_audit(target_python_path: str | Path) -> dict:
    """
    Run full audit on a target Python file and return the final scored payload.

    1. Run PromptScanner on file content (injection check).
    2. Run ComplianceEngine with empty config (SOC 2 + GDPR rule evaluation).
    3. Run AST PII scan on the file; convert findings to violations via PiiAdapter.
    4. Build Integrated Report and pass to build_result_payload().
    """
    path = Path(target_python_path)
    if not path.is_file():
        raise FileNotFoundError(f"Target file not found: {path}")

    # 1. Prompt injection scan (treat file content as input to check for injection patterns)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise RuntimeError(f"Cannot read file: {path}") from e

    scanner = PromptScanner()
    prompt_result = scanner.scan(content)
    prompt_injection = _prompt_result_to_dict(prompt_result)

    # 2. Compliance engine (SOC 2 and GDPR rules; empty config => report missing MFA, etc.)
    engine = ComplianceEngine.default()
    config: dict = {}
    engine_result = engine.evaluate(config)
    compliance_violations = [v.to_dict() for v in engine_result.violations]
    soc2_violations = [v.to_dict() for v in engine_result.violations if v.framework == "SOC2"]

    # 3. AST PII scan + PiiAdapter to violation format
    pii_scan_result = scan_python_file(path)
    pii_adapter = PiiAdapter()
    pii_violations = pii_adapter.scan_result_to_violations(pii_scan_result)
    compliance_violations.extend(v.to_dict() for v in pii_violations)

    # Quick regex scan for hardcoded secrets / API keys in file content
    secret_matches = _SECRET_PATTERN.findall(content)
    secrets_count = len(secret_matches)

    # 4. Integrated Report (schema expected by scoring_algorithm)
    integrated_report = {
        "target_file": str(path),
        "prompt_injection": prompt_injection,
        "compliance_violations": compliance_violations,
        "soc2_violations": soc2_violations,
        "pii_scan_results": [pii_scan_result.to_dict()],
        "secrets_or_api_keys": secrets_count,
    }

    # 5. Final Vibe-to-Value score and payload
    return build_result_payload(integrated_report, include_report=True)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python vibe_audit_engine.py <target_python_file>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    try:
        payload = run_audit(target)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(3)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
