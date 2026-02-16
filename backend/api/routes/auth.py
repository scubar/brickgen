"""Authentication routes."""
import logging
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.schemas import LoginRequest, TokenResponse
from backend.auth import authenticate_user, create_access_token, get_current_user
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    Args:
        login_request: Login credentials (username and password)
        
    Returns:
        TokenResponse with access token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    if not authenticate_user(login_request.username, login_request.password):
        logger.warning(f"Failed login attempt for username: {login_request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.jwt_expiration_minutes)
    access_token = create_access_token(
        data={"sub": login_request.username},
        expires_delta=access_token_expires
    )
    
    logger.info(f"User {login_request.username} logged in successfully")
    return TokenResponse(access_token=access_token)


@router.get("/verify")
async def verify_token(current_user: str = Depends(get_current_user)):
    """
    Verify JWT token is valid.
    
    Args:
        current_user: Current authenticated user (from token)
        
    Returns:
        dict with username if token is valid
    """
    return {"username": current_user, "authenticated": True}
