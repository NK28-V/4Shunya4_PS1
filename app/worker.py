"""
Celery worker: repository ingestion + unified scanning pipeline + persist ScanReport.

Unified pipeline: app.domain (security + compliance) + prompt_injection_scanner +
backend compliance_core (SOC2/GDPR + AST PII). All findings are aggregated into
a single ScanReport payload (including dataFlow for the frontend). Strict error
handling so one failed scanner does not crash the worker.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from celery import Celery
from sqlalchemy import select

# Project root on path for prompt_injection_scanner, backend.compliance_core
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.config import settings
from app.infrastructure.ingestion import ingest_repository as ingestion_service, cleanup_volume
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import (
    Scan,
    ScanStatus,
    Project,
    Vulnerability,
    ComplianceViolation,
)
from app.core.validators import validate_github_url

logger = logging.getLogger(__name__)

celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
)
celery_app.conf.task_routes = {
    "app.worker.scan_codebase": "main-queue",
}


def _collect_python_files(repo_path: str) -> list[tuple[str, str]]:
    """Return list of (absolute_path, relative_path) for each .py file under repo_path."""
    repo = Path(repo_path)
    if not repo.is_dir():
        return []
    out = []
    for p in repo.rglob("*.py"):
        if ".git" in p.parts or "venv" in p.parts or "__pycache__" in p.parts or p.name.startswith("."):
            continue
        try:
            rel = p.relative_to(repo)
            out.append((str(p.resolve()), str(rel)))
        except ValueError:
            continue
    return out


def _run_domain_security_scan(repo_path: str) -> list[dict]:
    """Run app.domain.security_scanner; return findings or [] on error."""
    try:
        from app.domain.security_scanner import run_security_scan
        return run_security_scan(repo_path)
    except Exception as e:
        logger.warning("Domain security scan failed: %s", e, exc_info=True)
        return []


def _run_domain_compliance_scan(repo_path: str) -> list[dict]:
    """Run app.domain.compliance_scanner; return findings or [] on error."""
    try:
        from app.domain.compliance_scanner import run_compliance_scan
        return run_compliance_scan(repo_path)
    except Exception as e:
        logger.warning("Domain compliance scan failed: %s", e, exc_info=True)
        return []


def _run_prompt_injection_scans(repo_path: str, py_files: list[tuple[str, str]]) -> list[dict]:
    """Run prompt_injection_scanner on each .py file content; return list of finding dicts."""
    findings = []
    try:
        from prompt_injection_scanner import PromptScanner
        scanner = PromptScanner()
    except Exception as e:
        logger.warning("Prompt injection scanner import failed: %s", e, exc_info=True)
        return findings

    for abs_path, rel_path in py_files:
        try:
            content = Path(abs_path).read_text(encoding="utf-8", errors="replace")
            result = scanner.scan(content)
            if result.is_injection or result.overall_score > 0:
                findings.append({
                    "severity": "HIGH" if result.is_injection else "MEDIUM",
                    "title": "Prompt injection risk",
                    "description": f"Layer scores L1={result.layer1_score:.2f} L2={result.layer2_score:.2f} L3={result.layer3_score:.2f}; type={result.layer3_type}. {result.layer3_explanation or ''}".strip(),
                    "file_path": rel_path,
                    "line_number": None,
                    "metadata": ["PROMPT_INJECTION", result.layer3_type] if result.layer3_type != "benign" else ["PROMPT_INJECTION"],
                })
        except Exception as e:
            logger.debug("Prompt injection scan failed for %s: %s", rel_path, e)
            continue
    return findings


def _run_compliance_core_engine() -> tuple[list[dict], list[dict]]:
    """Run backend ComplianceEngine (SOC2/GDPR) with empty config; return (violations, soc2_violations)."""
    try:
        from backend.compliance_core.engine import ComplianceEngine
        engine = ComplianceEngine.default()
        result = engine.evaluate({})
        violations = [v.to_dict() for v in result.violations]
        soc2 = [v for v in violations if v.get("framework") == "SOC2"]
        return violations, soc2
    except Exception as e:
        logger.warning("Compliance core engine failed: %s", e, exc_info=True)
        return [], []


def _run_pii_scans(repo_path: str, py_files: list[tuple[str, str]]) -> tuple[list[dict], list[dict]]:
    """Run backend AST PII scan + PiiAdapter on each .py file; return (violations, data_flow_edges)."""
    violations = []
    data_flow_edges = []
    try:
        from backend.compliance_core.ast_scanner import scan_python_file
        from backend.compliance_core.adapters.pii_adapter import PiiAdapter
        adapter = PiiAdapter()
    except Exception as e:
        logger.warning("PII scanner import failed: %s", e, exc_info=True)
        return violations, data_flow_edges

    for abs_path, rel_path in py_files:
        try:
            pii_result = scan_python_file(abs_path)
            vs = adapter.scan_result_to_violations(pii_result)
            for v in vs:
                violations.append(v.to_dict())
            for f in pii_result.findings:
                data_flow_edges.append({
                    "from": rel_path,
                    "to": "PII Sink",
                    "encrypted": False,
                    "containsPII": True,
                })
        except Exception as e:
            logger.debug("PII scan failed for %s: %s", rel_path, e)
            continue
    return violations, data_flow_edges


def _build_data_flow(
    domain_compliance: list[dict],
    core_violations: list[dict],
    pii_edges: list[dict],
) -> list[dict]:
    """Build unified dataFlow array for ScanReport (from, to, encrypted, containsPII)."""
    flow = list(pii_edges)
    seen = {((e.get("from") or ""), (e.get("to") or "")): True for e in flow}

    for v in domain_compliance:
        rule_id = v.get("rule_id", "COMPLIANCE")
        key = ("Repository", rule_id)
        if key not in seen:
            seen[key] = True
            flow.append({"from": "Repository", "to": rule_id, "encrypted": False, "containsPII": False})

    for v in core_violations:
        control = v.get("control", v.get("id", "SOC2/GDPR"))
        key = ("Config", control)
        if key not in seen:
            seen[key] = True
            flow.append({"from": "Config", "to": control, "encrypted": False, "containsPII": False})

    return flow


def _unified_scan(repo_path: str, project_name: str, scan_id: int, initiated_at: datetime) -> dict:
    """
    Run all scanners and return a single ScanReport-shaped payload.
    Each scanner is wrapped in try/except so one failure does not crash the run.
    """
    py_files = _collect_python_files(repo_path)

    security_findings = _run_domain_security_scan(repo_path)
    domain_compliance = _run_domain_compliance_scan(repo_path)
    prompt_findings = _run_prompt_injection_scans(repo_path, py_files)
    core_violations, _soc2 = _run_compliance_core_engine()
    pii_violations, pii_flow = _run_pii_scans(repo_path, py_files)

    all_findings = []
    for f in security_findings:
        all_findings.append({
            "severity": f.get("severity", "MEDIUM"),
            "title": f.get("title", ""),
            "description": f.get("description", ""),
            "file_path": f.get("file_path", ""),
            "line_number": f.get("line_number"),
            "metadata": ["AI_HALLUCINATED"] if "Unknown Dependency" in (f.get("title") or "") else [],
        })
    for c in domain_compliance:
        all_findings.append({
            "severity": (c.get("severity") or "MEDIUM").upper(),
            "title": c.get("rule_id", "Compliance"),
            "description": c.get("description", ""),
            "file_path": "",
            "line_number": None,
            "metadata": [c.get("rule_id", "")],
        })
    for f in prompt_findings:
        all_findings.append(f)

    try:
        from app.domain.scoring import RiskScorer
        scorer = RiskScorer()
        score, grade = scorer.calculate_risk_score(all_findings)
    except Exception as e:
        logger.warning("Risk scoring failed: %s", e, exc_info=True)
        score, grade = 0, "F"

    vulnerabilities_payload = []
    idx = 0
    for f in all_findings:
        idx += 1
        sev = (f.get("severity") or "LOW").upper()
        if sev not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            sev = "MEDIUM"
        meta = f.get("metadata") or []
        if not isinstance(meta, list):
            meta = [str(meta)]
        vulnerabilities_payload.append({
            "id": f"v_{scan_id}_{idx}",
            "file": f.get("file_path", ""),
            "severity": sev,
            "metadata": meta,
        })

    for v in core_violations + pii_violations:
        idx += 1
        msg = v.get("message", v.get("description", ""))
        severity = (v.get("severity") or "medium").upper()
        if severity not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            severity = "MEDIUM"
        vulnerabilities_payload.append({
            "id": f"v_{scan_id}_{idx}",
            "file": v.get("path", ""),
            "severity": severity,
            "metadata": [v.get("id", ""), msg],
        })

    data_flow = _build_data_flow(domain_compliance, core_violations, pii_flow)

    report = {
        "id": str(scan_id),
        "projectName": project_name or "",
        "score": max(0, min(100, score)),
        "codeCoverage": 0,
        "criticalIssues": sum(1 for v in vulnerabilities_payload if v.get("severity") == "CRITICAL"),
        "alertingConfigured": False,
        "availabilitySLO": 0,
        "deploymentBlocked": score < 60,
        "createdAt": initiated_at.isoformat() if initiated_at else datetime.utcnow().isoformat(),
        "status": "COMPLETED",
        "vulnerabilities": vulnerabilities_payload,
        "dataFlow": data_flow,
    }
    return report


@celery_app.task(name="scan_codebase")
def scan_codebase(scan_id: int):
    """
    Ingest repo, run unified scanning pipeline, persist Scan + Vulnerability + ComplianceViolation + report_payload.
    Cleanup temp directory on success or failure.
    """
    async def run_scan():
        async with SessionLocal() as db:
            result = await db.execute(select(Scan).where(Scan.id == scan_id))
            db_scan = result.scalar_one_or_none()
            if not db_scan:
                logger.error("Scan %s not found.", scan_id)
                return {"scan_id": scan_id, "status": "FAILED", "error": "Not found"}

            result = await db.execute(select(Project).where(Project.id == db_scan.project_id))
            project = result.scalar_one_or_none()
            if not project:
                db_scan.status = ScanStatus.FAILED
                await db.commit()
                logger.error("Project not found for scan %s.", scan_id)
                return {"scan_id": scan_id, "status": "FAILED", "error": "Project not found"}

            db_scan.status = ScanStatus.INGESTING
            await db.commit()
            logger.info("Scan %s status set to INGESTING.", scan_id)

            if not validate_github_url(project.repository_url):
                logger.error("Invalid repository URL for scan %s: %s", scan_id, project.repository_url)
                db_scan.status = ScanStatus.FAILED
                await db.commit()
                return {"scan_id": scan_id, "status": "FAILED", "error": "Invalid URL"}

            try:
                logger.info("Ingesting repository for scan %s: %s", scan_id, project.repository_url)
                ingestion_result = ingestion_service(project.repository_url)
                db_scan.container_id = ingestion_result["container_id"]
                db_scan.local_path = ingestion_result["local_path"]
                await db.commit()
                db_scan.status = ScanStatus.SCANNING
                await db.commit()
                logger.info("Ingestion successful for Scan %s, local path: %s", scan_id, db_scan.local_path)
            except Exception as e:
                logger.exception("Ingestion failed for Scan %s: %s", scan_id, e)
                db_scan.status = ScanStatus.FAILED
                await db.commit()
                return {"scan_id": scan_id, "status": "FAILED", "error": f"Ingestion failed: {e}"}

            try:
                repo_path = db_scan.local_path
                logger.info("Running unified scanners on %s for scan %s...", repo_path, scan_id)

                report = _unified_scan(
                    repo_path,
                    project.name,
                    scan_id,
                    db_scan.initiated_at or datetime.utcnow(),
                )

                score = report.get("score", 0)
                try:
                    from app.domain.scoring import RiskScorer
                    scorer = RiskScorer()
                    all_f = [{"severity": v.get("severity", "LOW")} for v in report.get("vulnerabilities", [])]
                    score, grade = scorer.calculate_risk_score(all_f)
                except Exception:
                    grade = "F" if score < 60 else "D" if score < 70 else "C" if score < 80 else "B" if score < 90 else "A"

                db_scan.score = score
                db_scan.grade = grade
                db_scan.report_payload = json.dumps(report)
                db_scan.status = ScanStatus.COMPLETED
                db_scan.finished_at = datetime.utcnow()

                for v in report.get("vulnerabilities", [])[:500]:
                    meta = v.get("metadata") or []
                    title = (meta[0] if isinstance(meta, list) and meta else None) or v.get("file", "")
                    desc = "; ".join(str(x) for x in meta) if isinstance(meta, list) else str(meta)
                    try:
                        from app.domain.remediation import get_remediation_tip
                        remediation_tip = get_remediation_tip(title, desc)
                    except Exception:
                        remediation_tip = None
                    db.add(
                        Vulnerability(
                            scan_id=scan_id,
                            severity=v.get("severity", "MEDIUM"),
                            title=title if isinstance(title, str) and len(title) <= 255 else None,
                            description=desc or v.get("file", ""),
                            file_path=v.get("file", ""),
                            line_number=None,
                            remediation_tip=remediation_tip,
                        )
                    )

                for v in report.get("vulnerabilities", [])[:500]:
                    mid = v.get("metadata") or []
                    if any("SOC2" in str(m) or "GDPR" in str(m) or "RESTRICTIVE" in str(m) or "PROMPT" in str(m) for m in mid):
                        db.add(
                            ComplianceViolation(
                                scan_id=scan_id,
                                rule_id=(mid[0][:100] if mid else "COMPLIANCE"),
                                description=v.get("file", "") or "; ".join(str(x) for x in mid),
                                severity=v.get("severity", "medium"),
                            )
                        )

                await db.commit()
                logger.info("Finished scan %s. Score=%s Grade=%s", scan_id, score, grade)
            except Exception as e:
                logger.exception("Scanning failed for Scan %s: %s", scan_id, e)
                db_scan.status = ScanStatus.FAILED
                await db.commit()

            cleanup_path = db_scan.container_id
            if cleanup_path:
                try:
                    cleanup_volume(cleanup_path)
                except Exception as cleanup_err:
                    logger.warning("Cleanup failed for %s: %s", cleanup_path, cleanup_err)

            return {
                "scan_id": scan_id,
                "status": db_scan.status.value,
                "score": db_scan.score,
                "grade": db_scan.grade,
            }

    return asyncio.run(run_scan())
