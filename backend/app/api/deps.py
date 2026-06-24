from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from uuid import UUID

from app.core.database import get_session
from app.core.security import decode_token
from app.core.token_store import is_token_revoked
from app.models.user import User
from app.schemas.auth import TokenPayload


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        token_data = TokenPayload(sub=payload.get("sub"))
        if token_data.sub is None or payload.get("type") != "access":
            raise credentials_exception
        jti = payload.get("jti")
        if not jti or is_token_revoked(jti):
            raise credentials_exception
    except Exception as exc:
        raise credentials_exception from exc

    try:
        user_id = UUID(token_data.sub)
    except (TypeError, ValueError) as exc:
        raise credentials_exception from exc

    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise credentials_exception

    return user


def require_roles(*allowed_roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return dependency
