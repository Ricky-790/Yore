import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import OAuthToken, User, UserSession

SESSION_TTL_SECONDS = 30 * 24 * 60 * 60


async def _upsert_google_token(token: dict, user: User, session: AsyncSession) -> None:
    oauth_token = await session.scalar(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == "google",
        )
    )
    if oauth_token is None:
        oauth_token = OAuthToken(user_id=user.id, provider="google")
        session.add(oauth_token)

    oauth_token.access_token = token["access_token"]
    oauth_token.refresh_token = token.get("refresh_token") or oauth_token.refresh_token
    oauth_token.scope = token.get("scope")
    oauth_token.token_type = token.get("token_type")

    expires_at = token.get("expires_at")
    if expires_at is not None:
        oauth_token.expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)
    elif token.get("expires_in") is not None:
        oauth_token.expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token["expires_in"]
        )


async def _create_session(user: User, session: AsyncSession) -> str:
    session_id = secrets.token_urlsafe(32)
    session.add(
        UserSession(
            id_hash=hashlib.sha256(session_id.encode()).hexdigest(),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS),
        )
    )
    await session.commit()
    return session_id


async def sign_in_google(token: dict, session: AsyncSession) -> str:
    userinfo = token["userinfo"]
    google_sub = userinfo["sub"]
    email = userinfo.get("email")

    user = await session.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        user = User(google_sub=google_sub, email=email)
        session.add(user)
        await session.flush()
    elif email and user.email != email:
        user.email = email

    await _upsert_google_token(token, user, session)
    return await _create_session(user, session)


async def get_google_token(user_id: int, session: AsyncSession) -> OAuthToken | None:
    return await session.scalar(
        select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "google",
        )
    )
