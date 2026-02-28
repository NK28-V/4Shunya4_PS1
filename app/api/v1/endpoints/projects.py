from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.infrastructure.models import Project
from pydantic import BaseModel
from typing import List

from app.core.security import limiter
from fastapi import Request

router = APIRouter()

class ProjectSchema(BaseModel):
    name: str
    repository_url: str

@router.post("/", response_model=ProjectSchema)
@limiter.limit("5/minute")
async def create_project(request: Request, project: ProjectSchema, db: AsyncSession = Depends(get_db)):
    if not project.repository_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid repository URL")
    
    db_project = Project(name=project.name, repository_url=project.repository_url)
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[ProjectSchema])
async def list_projects(db: AsyncSession = Depends(get_db)):
    # Simpler query for demonstration
    from sqlalchemy import select
    result = await db.execute(select(Project))
    return result.scalars().all()
