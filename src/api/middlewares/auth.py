import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.db.database import AsyncSessionLocal
from src.db.models import UserSession

PUBLIC_PATHS = ("/auth", "/docs", "/openapi.json", "/redoc")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path == prefix or path.startswith(prefix + "/") for prefix in PUBLIC_PATHS):
            return await call_next(request)

        token = request.cookies.get("yore_session")
        if not token:
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        async with AsyncSessionLocal() as session:
            active = await session.scalar(
                select(UserSession).where(
                    UserSession.id_hash == hashlib.sha256(token.encode()).hexdigest(),
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > datetime.now(timezone.utc),
                )
            )
            if active is None:
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            request.state.user_id = active.user_id

        return await call_next(request)
