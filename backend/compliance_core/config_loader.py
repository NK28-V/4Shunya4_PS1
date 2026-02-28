from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ConfigError(Exception):
    code: str
    message: str
    evidence: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def load_config_from_str(raw_json: str) -> dict[str, Any]:
    # Windows editors sometimes write a UTF-8 BOM; json.loads doesn't accept it.
    raw_json = raw_json.lstrip("\ufeff")
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ConfigError(
            code="CONFIG.JSON.PARSE_ERROR",
            message="Configuration file is not valid JSON.",
            evidence={"error": str(e)},
        ) from e

    if not isinstance(data, dict):
        raise ConfigError(
            code="CONFIG.JSON.INVALID_TYPE",
            message="Top-level JSON value must be an object.",
            evidence={"type": type(data).__name__},
        )

    return data


def load_config_from_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8-sig")
    except OSError as e:
        raise ConfigError(
            code="CONFIG.FILE.READ_ERROR",
            message="Could not read configuration file.",
            evidence={"path": str(p), "error": str(e)},
        ) from e

    return load_config_from_str(raw)

