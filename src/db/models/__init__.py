from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from src.db.models.oauth_token import OAuthToken
from src.db.models.session import UserSession
from src.db.models.user import User

__all__ = ["Base", "OAuthToken", "User", "UserSession"]
