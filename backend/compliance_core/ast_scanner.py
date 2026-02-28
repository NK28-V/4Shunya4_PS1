from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Simple mapping from name fragments to a PII type label.
PII_KEYWORDS: dict[str, str] = {
    "email": "email",
    "phone": "phone",
    "mobile": "phone",
    "ssn": "ssn",
    "social_security": "ssn",
    "password": "password",
    "passwd": "password",
    "pwd": "password",
}


@dataclass(slots=True)
class PiiFinding:
    """
    A single PII-related variable detected in Python source code.
    """

    name: str
    pii_type: str
    lineno: int
    col_offset: int
    context: str
    filename: str = ""
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
    "name": self.name,
    "pii_type": self.pii_type,
    "lineno": self.lineno,
    "col_offset": self.col_offset,
    "context": self.context,
    "filename": self.filename,
    "severity": self.severity,
}


@dataclass(slots=True)
class PiiScanResult:
    """
    Container for all findings in a single file.
    """

    file: str
    findings: list[PiiFinding] = field(default_factory=list)
    # If parsing fails or file cannot be read, this holds a human-readable note.
    error: str | None = None

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "findings": [f.to_dict() for f in self.findings],
            "finding_count": self.finding_count,
            "error": self.error,
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def _classify_pii_name(name: str) -> str | None:
    """
    Decide whether a variable name should be treated as PII.
    The check is simple: does the lowercased name contain any PII keyword?
    """
    lowered = name.lower()
    for fragment, pii_type in PII_KEYWORDS.items():
        if fragment in lowered:
            return pii_type
    return None


class _PiiVisitor(ast.NodeVisitor):
    """
    Walks the AST and records PII-like variable names.
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.findings: list[PiiFinding] = []

    # Helper methods -----------------------------------------------------

    def _add_finding(self, name: str, node: ast.AST, context: str) -> None:
        pii_type = _classify_pii_name(name)
        if not pii_type:
            return

        lineno = getattr(node, "lineno", 0)
        col_offset = getattr(node, "col_offset", 0)

        HIGH_RISK_TYPES = {"password", "ssn"}

        severity = "high" if pii_type.lower() in HIGH_RISK_TYPES else "medium"

        
        self.findings.append(
            PiiFinding(
                name=name,
                pii_type=pii_type,
                lineno=lineno,
                col_offset=col_offset,
                context=context,
                filename=self.filename,
                severity=severity,
            )
        )

    def _handle_target(self, target: ast.expr, context: str) -> None:
        # Covers patterns like x, user_email, self.password, (email, phone)
        if isinstance(target, ast.Name):
            self._add_finding(target.id, target, context)
        elif isinstance(target, ast.Attribute):
            # Example: self.password -> name is "password"
            self._add_finding(target.attr, target, context)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._handle_target(elt, context)

    # Visitor methods ----------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> Any:  # type: ignore[override]
        for target in node.targets:
            self._handle_target(target, context="assignment")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:  # type: ignore[override]
        if node.target is not None:
            self._handle_target(node.target, context="annotated_assignment")
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> Any:  # type: ignore[override]
        self._handle_target(node.target, context="for_loop")
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> Any:  # type: ignore[override]
        self._handle_target(node.target, context="for_loop")
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> Any:  # type: ignore[override]
        for item in node.items:
            if item.optional_vars is not None:
                self._handle_target(item.optional_vars, context="with_statement")
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> Any:  # type: ignore[override]
        for item in node.items:
            if item.optional_vars is not None:
                self._handle_target(item.optional_vars, context="with_statement")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # type: ignore[override]
        self._visit_function_args(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:  # type: ignore[override]
        self._visit_function_args(node)
        self.generic_visit(node)

    def _visit_function_args(self, node: ast.AST) -> None:
        # node.args is a `ast.arguments` object on both FunctionDef and AsyncFunctionDef
        args = getattr(node, "args", None)
        if args is None:
            return

        all_args = list(getattr(args, "posonlyargs", [])) + list(args.args) + list(args.kwonlyargs)
        if args.vararg is not None:
            all_args.append(args.vararg)
        if args.kwarg is not None:
            all_args.append(args.kwarg)

        for arg in all_args:
            if isinstance(arg, ast.arg):
                self._add_finding(arg.arg, arg, context="function_argument")


def scan_python_source(source: str, filename: str = "<memory>") -> PiiScanResult:
    """
    Scan a Python source string and return PII-related findings.

    If the source cannot be parsed (SyntaxError), the result will contain
    zero findings and the `error` field will describe the problem.
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        # Do not crash; return a result with an error note.
        message = f"SyntaxError: {e.msg}"
        if e.lineno:
            message += f" (line {e.lineno})"
        return PiiScanResult(file=filename, findings=[], error=message)

    visitor = _PiiVisitor(filename=filename)
    visitor.visit(tree)
    return PiiScanResult(file=filename, findings=visitor.findings, error=None)


def scan_python_file(path: str | Path) -> PiiScanResult:
    """
    Convenience helper to read a file from disk and scan it.
    """
    p = Path(path)
    try:
        source = p.read_text(encoding="utf-8")
    except OSError as e:
        return PiiScanResult(
            file=str(p),
            findings=[],
            error=f"Could not read file: {e}",
        )

    return scan_python_source(source, filename=str(p))

