from fastapi import APIRouter
from app.api.v1.endpoints import projects, scans

router = APIRouter()

router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(scans.router, prefix="/scans", tags=["scans"])
