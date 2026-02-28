from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings

# Redis-backed rate limiting for production (DDoS mitigation)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.celery_broker_url,
    default_limits=["60/minute"],
)

def setup_security(app):
    # CORS — tighten allow_origins in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust in production to explicit origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate Limiting (Redis-backed)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
