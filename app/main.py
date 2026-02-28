from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.security import setup_security
from app.core.logging import setup_logging
import logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Ensure 500 responses never leak stack traces, internal IPs, or PII to the client.
    Log full details server-side only.
    """
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
        headers={"X-Content-Type-Options": "nosniff"},
    )


# Setup CORS and Rate Limiting (after exception handler so handler is used)
setup_security(app)

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}", "docs": "/docs"}

# Include routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
