import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.security import setup_security
from app.core.logging import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Setup CORS and Rate Limiting
setup_security(app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure 500 responses never leak stack traces, internal IPs, or PII to the client."""
    logger.exception("Unhandled exception (not exposing to client): %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
        },
    )


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
