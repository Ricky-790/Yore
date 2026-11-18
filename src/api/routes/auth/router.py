import os

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_session
from src.db.services.accounts import SESSION_TTL_SECONDS, sign_in_google

load_dotenv()
router = APIRouter(prefix="/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    authorize_url=os.environ.get("GOOGLE_AUTH_URI", ""),
    access_token_url=os.environ.get("GOOGLE_TOKEN_URI", ""),
    jwks_uri=os.environ.get(
        "GOOGLE_JWKS_URI", "https://www.googleapis.com/oauth2/v3/certs"
    ),
    authorize_params={"access_type": "offline", "prompt": "select_account"},
    client_kwargs={
        "scope": "openid email https://www.googleapis.com/auth/gmail.readonly"
    },
)


def _session_response(session_id: str, request: Request) -> JSONResponse:
    response = JSONResponse({"detail": "signed in with Google"})
    response.set_cookie(
        "yore_session",
        session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
    return response


@router.get("/signin/google")
async def signin_google(request: Request):
    return await oauth.google.authorize_redirect(
        request, request.url_for("google_callback")
    )


@router.get("/google/callback", name="google_callback")
async def google_callback(
    request: Request, session: AsyncSession = Depends(get_session)
):
    token = await oauth.google.authorize_access_token(request)
    session_id = await sign_in_google(token, session)
    return _session_response(session_id, request)
