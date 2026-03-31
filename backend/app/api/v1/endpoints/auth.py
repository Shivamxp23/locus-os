from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.database import get_db
from app.models.models import User
from app.services.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user
)
from app.config import settings
from jose import jwt, JWTError

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=req.email,
        display_name=req.display_name,
        hashed_password=hash_password(req.password),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id)
    )

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await db.execute(
        User.__table__.update().where(User.id == user.id).values(last_active=datetime.utcnow())
    )
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id)
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(req.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id)
    )

@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "timezone": current_user.timezone,
        "genesis_completed": current_user.genesis_completed,
        "telegram_chat_id": current_user.telegram_chat_id,
        "google_connected": bool(current_user.google_refresh_token),
        "created_at": current_user.created_at
    }


@router.get("/google")
async def google_oauth_start(current_user: User = Depends(get_current_user)):
    """Redirect user to Google OAuth consent page."""
    from app.services.google_calendar import get_auth_url
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    url = get_auth_url(state=current_user.id)
    return {"auth_url": url}


@router.get("/google/callback")
async def google_oauth_callback(
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth redirect. Exchanges code for tokens and stores them on the user.
    Called by Google after the user grants consent.
    """
    from app.services.google_calendar import exchange_code_for_tokens
    from datetime import datetime, timedelta

    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")

    try:
        tokens = await exchange_code_for_tokens(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)

    # Use state as user_id (set during /auth/google)
    user_id = state
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing state/user_id")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.google_access_token = access_token
    if refresh_token:
        user.google_refresh_token = refresh_token
    user.google_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    user.updated_at = datetime.utcnow()
    await db.commit()

    return {"status": "connected", "message": "Google Calendar connected successfully"}
