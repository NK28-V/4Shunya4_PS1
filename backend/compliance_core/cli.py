from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a script from repo root: `python backend/compliance_core/cli.py ...`
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from compliance_core.config_loader import ConfigError, load_config_from_file  # noqa: E402
from compliance_core.models import Violation  # noqa: E402
from compliance_core.result import EngineResult  # noqa: E402
from compliance_core.engine import evaluate_config  # noqa: E402


def _config_error_result(err: ConfigError) -> EngineResult:
    v = Violation(
        id=err.code,
        framework="CONFIG",
        control="Configuration",
        severity="high",
        message=err.message,
        path="",
        evidence=err.evidence or {},
    )
    return EngineResult(violations=[v], frameworks_checked=[])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vibe-Audit compliance rules engine")
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args(argv)

    try:
        config = load_config_from_file(args.config)
    except ConfigError as e:
        result = _config_error_result(e)
        print(result.to_json(indent=2 if args.pretty else None))
        return 2

    result = evaluate_config(config)
    print(result.to_json(indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

