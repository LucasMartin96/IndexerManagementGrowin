"""
Authentication endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.auth import LoginRequest, TokenResponse
from app.models.user import CreateUserRequest, UserResponse
from app.services.auth_service import verify_user
from app.services.user_service import create_user
from app.core.security import create_access_token
from app.api.deps import require_full_access

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Login and get JWT token"""
    user = verify_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    access_token = create_access_token(data={"sub": str(user['id'])})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )


@router.post("/users", response_model=UserResponse)
async def create_user_endpoint(
    request: CreateUserRequest,
    current_user: dict = Depends(require_full_access)
) -> UserResponse:
    """
    Create a new user
    Access: JWT token only (full access required)
    """
    user = create_user(
        username=request.username,
        password=request.password,
        email=request.email,
        role=request.role
    )
    
    return UserResponse(**user)

