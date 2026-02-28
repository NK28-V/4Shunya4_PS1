from celery import Celery
from app.core.config import settings
from app.infrastructure.ingestion import ingest_repository as ingestion_service, cleanup_volume
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import Scan, ScanStatus, Project, Vulnerability, ComplianceViolation
from app.core.validators import validate_github_url
from app.domain.security_scanner import run_security_scan
from app.domain.compliance_scanner import run_compliance_scan
from app.domain.scoring import RiskScorer
from app.domain.remediation import get_remediation_tip
import asyncio
import logging
from datetime import datetime # Added for datetime.utcnow()

logger = logging.getLogger(__name__)

celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url
)

async def _process_scan(scan_id: int):
    """
    Asynchronous helper to handle the scan lifecycle.
    """
    async with SessionLocal() as db:
        # 1. Fetch Scan and Project
        from sqlalchemy import select
        result = await db.execute(
            select(Scan, Project)
            .join(Project, Scan.project_id == Project.id)
            .where(Scan.id == scan_id)
        )
        data = result.first()
        if not data:
            logger.error(f"Scan ID {scan_id} not found")
            return

        scan, project = data
        
        # 2. Update status to RUNNING
        scan.status = ScanStatus.RUNNING
        await db.commit()

        # 3. Trigger Ingestion
        logger.info(f"Ingesting repository for scan {scan_id}: {project.repository_url}")
celery_app.conf.task_routes = {
    "app.worker.scan_codebase": "main-queue",
}

@celery_app.task(name="scan_codebase")
def scan_codebase(scan_id: int):
    """
    Orchestrates repository ingestion and subsequent scanning.
    """
    async def run_scan():
        async with SessionLocal() as db:
            logger.info(f"Starting scan for ID: {scan_id}")
            # Fetch Scan and Project
            result = await db.execute(select(Scan).where(Scan.id == scan_id))
            db_scan = result.scalar_one_or_none()
            if not db_scan:
                logger.error(f"Scan {scan_id} not found.")
                return {"scan_id": scan_id, "status": "FAILED", "error": "Not found"}
                
            result = await db.execute(select(Project).where(Project.id == db_scan.project_id))
            project = result.scalar_one_or_none()
            if not project:
                db_scan.status = ScanStatus.FAILED
                await db.commit()
                logger.error(f"Project not found for scan {scan_id}.")
                return {"scan_id": scan_id, "status": "FAILED", "error": "Project not found"}
            
            db_scan.status = ScanStatus.INGESTING
            await db.commit()
            logger.info(f"Scan {scan_id} status set to INGESTING.")
            
            # Step 1: Strict Sanitization
            if not validate_github_url(project.repository_url):
                logger.error(f"Invalid repository URL for scan {scan_id}: {project.repository_url}")
                db_scan.status = ScanStatus.FAILED
                await db.commit()
                return {"scan_id": scan_id, "status": "FAILED", "error": "Invalid URL"}
                
            # Step 2: Containerized Isolation (Ingestion)
            try:
                logger.info(f"Ingesting repository for scan {scan_id}: {project.repository_url}")
                ingestion_result = ingestion_service(project.repository_url)
                db_scan.container_id = ingestion_result["container_id"]
                db_scan.local_path = ingestion_result["local_path"]
                await db.commit()
                db_scan.status = ScanStatus.SCANNING
                await db.commit()
                logger.info(f"Ingestion successful for Scan {scan_id}, local path: {db_scan.local_path}")
            except Exception as e:
                logger.exception(f"Ingestion failed for Scan {scan_id}: {e}")
                db_scan.status = ScanStatus.FAILED
                await db.commit()
                return {"scan_id": scan_id, "status": "FAILED", "error": f"Ingestion failed: {e}"}

            # Step 3: Analysis Engine & Compliance Scanning
            # TODO(PRODUCTION): ingest_repository returns local_path (e.g. "/data/repo") inside the
            # Docker container. If the Celery worker runs on the host, it cannot read this path.
            # For production deployment, ensure the Celery worker and the ingestion container share
            # the same mounted volume (e.g. run the worker in a container that mounts the same volume).
            try:
                repo_path = db_scan.local_path
                logger.info(f"Running scanners on {repo_path} for scan {scan_id}...")
                
                # Run Scanners
                security_vulns = run_security_scan(repo_path)
                compliance_issues = run_compliance_scan(repo_path)
                
                # Risk Scoring
                combined_findings = security_vulns + compliance_issues
                scorer = RiskScorer()
                score, grade = scorer.calculate_risk_score(combined_findings)
                
                db_scan.score = score
                db_scan.grade = grade
                
                # Persist Vulnerabilities
                for v in security_vulns:
                    db_vuln = Vulnerability(
                        scan_id=scan_id,
                        severity=v["severity"],
                        title=v.get("title", ""),
                        description=v["description"],
                        file_path=v["file_path"],
                        line_number=v.get("line_number"),
                        remediation_tip=get_remediation_tip(v.get("title", ""), v.get("description", ""))
                    )
                    db.add(db_vuln)
                
                # Persist Compliance Violations
                for c in compliance_issues:
                    db_compliance = ComplianceViolation(
                        scan_id=scan_id,
                        rule_id=c["rule_id"],
                        description=c["description"],
                        severity=c["severity"]
                    )
                    db.add(db_compliance)
                
                db_scan.status = ScanStatus.COMPLETED
                db_scan.finished_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"Finished scan for ID: {scan_id}. Found {len(security_vulns)} vulns and {len(compliance_issues)} issues.")
                
                # Step 4: Cleanup
                volume_name = db_scan.container_id
                if volume_name:
                    cleanup_volume(volume_name)
                
                return {"scan_id": scan_id, "status": "COMPLETED"}

            except Exception as e:
                logger.exception(f"Scanning failed for Scan {scan_id}: {e}")
                db_scan.status = ScanStatus.FAILED
                await db.commit()
                
                volume_name = db_scan.container_id
                if volume_name:
                    cleanup_volume(volume_name)
                    
                return {"scan_id": scan_id, "status": "FAILED", "error": f"Scanning failed: {e}"}

    # Celery tasks are synchronous, we run the async code inside an event loop
    return asyncio.run(run_scan())
