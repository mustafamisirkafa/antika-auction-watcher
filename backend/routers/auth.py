"""
Authentication routes with JWT refresh token support (Sprint 2).

Endpoints:
- POST /auth/register: Register new user
- POST /auth/login: Login and get access + refresh tokens
- POST /auth/refresh: Refresh access token using refresh token
- POST /auth/logout: Revoke refresh token
- GET /auth/me: Get current user info
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr
from typing import Optional

from backend.db.database import get_session
from backend.db.models import User
from backend.core.auth_enhanced import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    store_refresh_token,
    verify_stored_refresh_token,
    revoke_refresh_token,
    get_current_user_enhanced,
    TokenResponse,
    RefreshTokenRequest,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_HOURS,
)
from backend.core.security import get_client_ip, get_user_agent
from backend.middleware.team_context import get_redis
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


class UserRegister(BaseModel):
    """User registration schema."""
    email: EmailStr
    username: str
    password: str


class UserResponse(BaseModel):
    """User response schema."""
    id: int
    email: str
    username: str
    is_active: bool


class Token(BaseModel):
    """Legacy token response schema (for compatibility)."""
    access_token: str
    token_type: str


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """
    Dependency to get current authenticated user.
    
    Note: This is the legacy version. Use get_current_user_enhanced for new endpoints.
    """
    from backend.core.auth_enhanced import verify_access_token
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik do?rulama ba?ar?s?z",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        user_id = verify_access_token(token)
    except HTTPException:
        raise credentials_exception
    
    if user_id is None:
        raise credentials_exception
    
    user = session.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, session: Session = Depends(get_session)):
    """
    Register a new user.
    
    Returns user info (without tokens - must login separately).
    """
    # Check if user already exists
    statement = select(User).where(
        (User.email == user_data.email) | (User.username == user_data.username)
    )
    existing_user = session.exec(statement).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-posta veya kullan?c? ad? zaten kay?tl?"
        )
    
    # Create new user
    hashed_pwd = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_pwd
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
    redis = Depends(get_redis)
):
    """
    Login and get access + refresh tokens.
    
    Tokens are bound to user-agent and IP for security.
    """
    # Find user by username
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullan?c? ad? veya ?ifre hatal?",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hesap aktif de?il"
        )
    
    # Extract security context
    user_agent = get_user_agent(request)
    client_ip = get_client_ip(request)
    
    # Create tokens
    access_token = create_access_token(
        user_id=str(user.id),
        user_agent=user_agent,
        ip_address=client_ip
    )
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        user_agent=user_agent,
        ip_address=client_ip
    )
    
    # Store refresh token in Redis
    await store_refresh_token(str(user.id), refresh_token, redis)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    redis = Depends(get_redis)
):
    """
    Refresh access token using a valid refresh token.
    
    The refresh token must:
    - Be valid and not expired
    - Match the stored token in Redis
    - Have matching user-agent and IP (if binding was used)
    """
    try:
        # Verify refresh token structure and expiration
        user_id = verify_refresh_token(refresh_request.refresh_token)
        
        # Verify token matches stored token in Redis
        is_valid = await verify_stored_refresh_token(user_id, refresh_request.refresh_token, redis)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token ge?ersiz veya iptal edilmi?"
            )
        
        # Extract security context
        user_agent = get_user_agent(request)
        client_ip = get_client_ip(request)
        
        # Create new access token (with same binding)
        new_access_token = create_access_token(
            user_id=user_id,
            user_agent=user_agent,
            ip_address=client_ip
        )
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=None,  # Don't issue new refresh token
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yenileme ba?ar?s?z"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """
    Logout by revoking the user's refresh token.
    
    Access tokens remain valid until expiration (short-lived: 1 hour).
    """
    await revoke_refresh_token(str(current_user.id), redis)
    return None


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user
