from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.infrastructure.database import get_db
from app.infrastructure.models import Scan, ScanStatus, Project, Vulnerability, ComplianceViolation
from app.worker import scan_codebase
from pydantic import BaseModel
from typing import Any, Optional
import json

from app.core.security import limiter
from fastapi import Request
from sqlalchemy import select

router = APIRouter()


def _scan_to_report_payload(db_scan: Scan, project: Optional[Project] = None) -> dict[str, Any]:
    """Build ScanReport-shaped payload from Scan (and optional report_payload)."""
    report_payload = getattr(db_scan, "report_payload", None)
    if report_payload:
        try:
            payload = json.loads(report_payload)
            # Overwrite with current DB values
            payload["id"] = str(db_scan.id)
            payload["projectName"] = (project.name if project else "") or payload.get("projectName", "")
            payload["createdAt"] = (db_scan.initiated_at.isoformat() if db_scan.initiated_at else "") or payload.get("createdAt", "")
            payload["status"] = "COMPLETED" if db_scan.status == ScanStatus.COMPLETED else "PROCESSING"
            payload["score"] = db_scan.score if db_scan.score is not None else payload.get("score", 0)
            return payload
        except (json.JSONDecodeError, TypeError):
            pass
    # Build from relations
    vulns = getattr(db_scan, "vulnerabilities", []) or []
    violations = getattr(db_scan, "violations", []) or []
    vulnerabilities = [
        {
            "id": str(v.id),
            "file": v.file_path or "",
            "severity": (v.severity or "LOW").upper(),
            "metadata": [v.title or "", v.description or ""] if v.title or v.description else [],
        }
        for v in vulns
    ]
    data_flow = getattr(db_scan, "_data_flow", [])
    return {
        "id": str(db_scan.id),
        "projectName": project.name if project else "",
        "score": db_scan.score if db_scan.score is not None else 0,
        "codeCoverage": 0,
        "criticalIssues": sum(1 for v in vulns if (v.severity or "").upper() == "CRITICAL"),
        "alertingConfigured": False,
        "availabilitySLO": 0,
        "deploymentBlocked": (db_scan.score is not None and db_scan.score < 60),
        "createdAt": db_scan.initiated_at.isoformat() if db_scan.initiated_at else "",
        "status": "COMPLETED" if db_scan.status == ScanStatus.COMPLETED else "PROCESSING",
        "vulnerabilities": vulnerabilities,
        "dataFlow": data_flow,
    }


class ScanCreate(BaseModel):
    project_id: int


@router.post("/{project_id}/trigger")
@limiter.limit("5/minute")
async def trigger_scan(request: Request, project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_scan = Scan(project_id=project_id, status=ScanStatus.PENDING)
    db.add(db_scan)
    await db.commit()
    await db.refresh(db_scan)

    scan_codebase.delay(db_scan.id)

    return {"message": "Scan triggered", "scan_id": db_scan.id}


@router.get("/{scan_id}")
async def get_scan_status(scan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scan)
        .where(Scan.id == scan_id)
        .options(selectinload(Scan.project), selectinload(Scan.vulnerabilities), selectinload(Scan.violations))
    )
    db_scan = result.scalar_one_or_none()
    if not db_scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    project = db_scan.project
    return _scan_to_report_payload(db_scan, project)
