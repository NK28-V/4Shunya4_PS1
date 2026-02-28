"""
Celery worker: repository ingestion + Vibe Audit Engine (run_audit) + persist to DB.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

from celery import Celery
from sqlalchemy import select

from app.core.config import settings
from app.infrastructure.ingestion import ingest_repository as ingestion_service, cleanup_volume
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import Scan, ScanStatus, Project, ComplianceViolation
from app.core.validators import validate_github_url

# Ensure project root is on path so vibe_audit_engine and its deps resolve
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from vibe_audit_engine import run_audit

logger = logging.getLogger(__name__)

celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
)
celery_app.conf.task_routes = {
    "app.worker.scan_codebase": "main-queue",
}


def _resolve_audit_target(repo_path: str) -> Path:
    """
    Resolve the cloned repository path to a single Python file for run_audit().
    Prefer main.py at repo root, then app/main.py, then first *.py found.
    """
    root = Path(repo_path)
    if root.is_file() and root.suffix == ".py":
        return root
    if not root.is_dir():
        raise FileNotFoundError(f"Repository path is not a directory: {repo_path}")
    for candidate in ("main.py", "app/main.py"):
        p = root / candidate
        if p.is_file():
            return p
    first_py = next(root.rglob("*.py"), None)
    if first_py is not None:
        return first_py
    raise FileNotFoundError(f"No Python file found under repository: {repo_path}")


@celery_app.task(name="scan_codebase")
def scan_codebase(scan_id: int):
    """
    Ingest repository, run vibe audit (run_audit), then save score and
    integrated report to the database.
    """

    async def run_scan():
        async with SessionLocal() as db:
            logger.info("Starting scan for ID: %s", scan_id)
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
                logger.info("Running vibe audit on %s for scan %s...", repo_path, scan_id)

                target_path = _resolve_audit_target(repo_path)
                payload = run_audit(target_path)

                vibe_to_value_score = payload.get("vibe_to_value_score")
                integrated_report = payload.get("integrated_report")

                db_scan.vibe_to_value_score = vibe_to_value_score
                db_scan.integrated_report = json.dumps(integrated_report) if integrated_report is not None else None
                db_scan.status = ScanStatus.COMPLETED
                db_scan.finished_at = datetime.utcnow()

                # Persist compliance violations from integrated report into existing model
                if integrated_report:
                    for v in integrated_report.get("compliance_violations") or []:
                        if isinstance(v, dict):
                            db.add(
                                ComplianceViolation(
                                    scan_id=scan_id,
                                    rule_id=v.get("id", "")[:100],
                                    description=v.get("message", ""),
                                    severity=v.get("severity", "medium"),
                                )
                            )

                await db.commit()
                logger.info(
                    "Finished scan %s. Vibe-to-Value score: %s",
                    scan_id,
                    vibe_to_value_score,
                )

                volume_name = db_scan.container_id
                if volume_name:
                    cleanup_volume(volume_name)

                return {"scan_id": scan_id, "status": "COMPLETED", "vibe_to_value_score": vibe_to_value_score}

            except Exception as e:
                logger.exception("Scanning failed for Scan %s: %s", scan_id, e)
                db_scan.status = ScanStatus.FAILED
                await db.commit()

                volume_name = db_scan.container_id
                if volume_name:
                    cleanup_volume(volume_name)

                return {"scan_id": scan_id, "status": "FAILED", "error": f"Scanning failed: {e}"}

    return asyncio.run(run_scan())
