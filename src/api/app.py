import os

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from src.api.middlewares.auth import AuthMiddleware
from src.api.routes.auth.router import router as auth_router
from src.api.routes.test.router import router as test_router

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET_KEY", "dev-only-secret-change-me"),
)
app.add_middleware(AuthMiddleware)
app.include_router(auth_router)
app.include_router(test_router)
