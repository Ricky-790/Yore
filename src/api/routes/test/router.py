from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.connector.gmail.service import fetch_emails, parse_time_span
from src.db.database import get_session
from src.db.services.accounts import get_google_token

router = APIRouter(prefix="/test", tags=["test"])


@router.get("")
async def test_email_fetch(
    time_span: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    try:
        span = parse_time_span(time_span)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    token = await get_google_token(request.state.user_id, session)
    if token is None:
        raise HTTPException(status_code=404, detail="Google account not connected")

    return await run_in_threadpool(fetch_emails, token, span)
