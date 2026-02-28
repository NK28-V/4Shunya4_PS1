from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.infrastructure.database import get_db
from app.infrastructure.models import Project
from pydantic import BaseModel
from typing import List
from sqlalchemy import select

from app.core.security import limiter
from app.core.validators import validate_github_url, ensure_no_ssrf_host

router = APIRouter()

class ProjectSchema(BaseModel):
    name: str
    repository_url: str

@router.post("/", response_model=ProjectSchema)
@limiter.limit("5/minute")
async def create_project(request: Request, project: ProjectSchema, db: AsyncSession = Depends(get_db)):
    if not validate_github_url(project.repository_url):
        raise HTTPException(status_code=400, detail="Invalid repository URL: only https://github.com/org/repo is allowed")
    try:
        ensure_no_ssrf_host(project.repository_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid repository URL")
    
    db_project = Project(name=project.name, repository_url=project.repository_url)
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[ProjectSchema])
@limiter.limit("60/minute")
async def list_projects(request: Request, db: AsyncSession = Depends(get_db)):
    # Simpler query for demonstration
    result = await db.execute(select(Project))
    return result.scalars().all()
