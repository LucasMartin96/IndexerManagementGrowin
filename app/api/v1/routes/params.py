"""
Parameter CRUD endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.models.param import CreateParamRequest, UpdateParamRequest, ParamResponse
from app.services.param_service import (
    create_param,
    get_param,
    update_param,
    delete_param,
    list_params,
    search_params,
    get_params_by_category,
    get_categories
)
from app.api.deps import require_full_access

router = APIRouter()


@router.post("", response_model=ParamResponse)
async def create_param_endpoint(
    request: CreateParamRequest,
    current_user: dict = Depends(require_full_access)
) -> ParamResponse:
    """
    Create a new parameter
    Access: JWT token only (full access required)
    """
    param = create_param(
        key=request.key,
        value=request.value,
        description=request.description,
        category=request.category
    )
    
    return ParamResponse(**param)


@router.get("/{key}", response_model=ParamResponse)
async def get_param_endpoint(
    key: str,
    current_user: dict = Depends(require_full_access)
) -> ParamResponse:
    """
    Get parameter by key
    Access: JWT token only (full access required)
    """
    param = get_param(key)
    if not param:
        raise HTTPException(status_code=404, detail=f"Parameter '{key}' not found")
    
    return ParamResponse(**param)


@router.put("/{key}", response_model=ParamResponse)
async def update_param_endpoint(
    key: str,
    request: UpdateParamRequest,
    current_user: dict = Depends(require_full_access)
) -> ParamResponse:
    """
    Update parameter by key
    Access: JWT token only (full access required)
    """
    success = update_param(
        key=key,
        value=request.value,
        description=request.description,
        category=request.category
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Parameter '{key}' not found")
    
    param = get_param(key)
    return ParamResponse(**param)


@router.delete("/{key}")
async def delete_param_endpoint(
    key: str,
    current_user: dict = Depends(require_full_access)
) -> dict:
    """
    Delete parameter by key
    Access: JWT token only (full access required)
    """
    success = delete_param(key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Parameter '{key}' not found")
    
    return {"status": "deleted", "key": key}


@router.get("", response_model=List[ParamResponse])
async def list_params_endpoint(
    category: Optional[str] = None,
    current_user: dict = Depends(require_full_access)
) -> List[ParamResponse]:
    """
    List all parameters
    Access: JWT token only (full access required)
    """
    params = list_params(category=category)
    return [ParamResponse(**param) for param in params]


@router.get("/search/{search_term}", response_model=List[ParamResponse])
async def search_params_endpoint(
    search_term: str,
    current_user: dict = Depends(require_full_access)
) -> List[ParamResponse]:
    """
    Search parameters
    Access: JWT token only (full access required)
    """
    params = search_params(search_term)
    return [ParamResponse(**param) for param in params]


@router.get("/categories/list", response_model=List[str])
async def get_categories_endpoint(
    current_user: dict = Depends(require_full_access)
) -> List[str]:
    """
    Get all categories
    Access: JWT token only (full access required)
    """
    return get_categories()


@router.get("/category/{category}", response_model=List[ParamResponse])
async def get_params_by_category_endpoint(
    category: str,
    current_user: dict = Depends(require_full_access)
) -> List[ParamResponse]:
    """
    Get parameters by category
    Access: JWT token only (full access required)
    """
    params = get_params_by_category(category)
    return [ParamResponse(**param) for param in params]

