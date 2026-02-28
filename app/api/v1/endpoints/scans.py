from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.infrastructure.models import Project, Scan, ScanStatus
from app.worker import scan_codebase
from pydantic import BaseModel

from app.core.security import limiter
from fastapi import Request

router = APIRouter()

class ScanCreate(BaseModel):
    project_id: int

@router.post("/{project_id}/trigger")
@limiter.limit("5/minute")
async def trigger_scan(request: Request, project_id: int, db: AsyncSession = Depends(get_db)):
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Create scan record in DB
    db_scan = Scan(project_id=project_id, status=ScanStatus.PENDING)
    db.add(db_scan)
    await db.commit()
    await db.refresh(db_scan)
    
    # 2. Trigger Celery task
    scan_codebase.delay(db_scan.id)
    
    return {"message": "Scan triggered", "scan_id": db_scan.id}

@router.get("/{scan_id}")
@limiter.limit("60/minute")
async def get_scan_status(request: Request, scan_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    db_scan = result.scalar_one_or_none()
    if not db_scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return db_scan
