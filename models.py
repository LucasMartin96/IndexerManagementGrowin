"""
Pydantic models for FastAPI request/response validation
"""

from pydantic import BaseModel, Field, validator, field_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


# ========================================
# Indexer Request Models
# ========================================

class IndexLicitacionRequest(BaseModel):
    """Request to index a single publication"""
    publicacion_id: int = Field(..., description="ID of the publication to index")


class IndexScraperRequest(BaseModel):
    """Request to index publications from a scraper"""
    scraper_id: int = Field(..., description="ID of the scraper")
    since: str = Field(..., description="Datetime in format YYYY-MM-DD HH:MM:SS")


class SyncSinceRequest(BaseModel):
    """Request to sync publications since a given date"""
    since: str = Field(..., description="Datetime in format YYYY-MM-DD HH:MM:SS")


# ========================================
# Search Request Model
# ========================================

class SearchLicitacionesRequest(BaseModel):
    """Request to search publications"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=15, ge=1, le=1000000, description="Items per page")
    incluirVencidos: Optional[str] = Field(default=None, description="'0' = only vigente, '1' = all")
    soloVigentes: Optional[str] = Field(default=None, description="'1' = only vigente publications")
    
    # Filter fields
    objeto: Optional[str] = Field(default=None, description="Search in objeto field")
    agencia: Optional[str] = Field(default=None, description="Search in agencia field")
    pais: Optional[str] = Field(default=None, description="Country ID or name, 'all' to ignore")
    rubro: Optional[str] = Field(default=None, description="Tag/rubro ID, 'all' to ignore")
    apertura_fr: Optional[str] = Field(default=None, description="Start date in DD/MM/YYYY format")
    apertura_to: Optional[str] = Field(default=None, description="End date in DD/MM/YYYY format")
    search: Optional[str] = Field(default=None, description="General search query")
    
    # User tag filtering
    user_tag_ids: Optional[List[int]] = Field(default=None, description="Array of user-selected tag IDs")
    filter_mode: Optional[str] = Field(default="all", description="'user_tags' or 'all'")


# ========================================
# Response Models
# ========================================

class IndexResponse(BaseModel):
    """Response for indexing operations"""
    status: str
    id: Optional[int] = None
    scraper_id: Optional[int] = None
    since: Optional[str] = None
    indexed: Optional[int] = None
    total: Optional[int] = None
    failed: Optional[int] = None
    total_indexed: Optional[int] = None
    total_failed: Optional[int] = None
    timestamp: Optional[str] = None


class TagModel(BaseModel):
    """Tag model for search results"""
    id: int
    descripcion: str


class PublicationModel(BaseModel):
    """Publication model for search results"""
    model_config = {
        "json_encoders": {
            # Custom JSON encoders if needed
        },
        # Include all fields in response, even if None
        "exclude_none": False
    }
    
    id: int
    scraper: Optional[int] = None
    idexterno: Optional[str] = None
    referencia: Optional[str] = None
    objeto: Optional[str] = None
    agencia: Optional[str] = None
    oficina: Optional[str] = None
    link: Optional[str] = None
    publicado: Optional[str] = None
    actualizado: Optional[str] = None
    apertura: Optional[str] = None
    cierre: Optional[str] = None
    pais: Optional[str] = None
    rubro: Optional[str] = None
    subrubro: Optional[str] = None
    tipo: Optional[str] = None
    tipo_id: Optional[int] = None
    tipo_cliente_id: Optional[str] = None
    contacto: Optional[str] = None
    observaciones: Optional[str] = None
    categoria: Optional[int] = None
    cargado: Optional[str] = None
    editado: Optional[str] = None
    visible: Optional[bool] = None
    attachs: Optional[str] = None
    monto: Optional[float] = None
    
    @field_validator('tipo_cliente_id', mode='before')
    @classmethod
    def convert_tipo_cliente_id(cls, v):
        """Convert tipo_cliente_id to string if it's an int"""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return str(v)
        return str(v) if v else None
    
    @field_validator('monto', mode='before')
    @classmethod
    def convert_monto(cls, v):
        """Convert empty string or invalid monto to None"""
        if v is None:
            return None
        if isinstance(v, str):
            if v.strip() == '' or v == '0':
                return None
            try:
                return float(v)
            except ValueError:
                return None
        try:
            return float(v) if v else None
        except (ValueError, TypeError):
            return None
    divisaSimboloISO: Optional[str] = None
    tags: Optional[List[TagModel]] = None
    tag_ids: Optional[List[int]] = None
    mercado_ids: Optional[List[int]] = None
    tipo_licit_ids: Optional[Dict[str, Optional[int]]] = None
    tasaCambioUSD: Optional[float] = None
    pais_nombre: Optional[str] = None
    pais_id: Optional[int] = None
    vigente: Optional[bool] = None
    
    @field_validator('tag_ids', 'mercado_ids', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """Ensure arrays are lists, not None or empty strings"""
        if v is None or v == '':
            return []
        if isinstance(v, list):
            return v
        return [v] if v else []


class SearchResponse(BaseModel):
    """Response for search operations"""
    publicaciones: List[PublicationModel]
    total: int
    pagina: int
    paginas: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    scheduler_running: bool


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    message: str

# ========================================
# Auth Models
# ========================================

class CreateAPIKeyRequest(BaseModel):
    """Request to create API key"""
    name: str
    user_id: Optional[int] = None
    permissions: Optional[str] = None
    expires_days: Optional[int] = None

class APIKeyResponse(BaseModel):
    """API key response (with plaintext key only on creation)"""
    key_id: int
    key: Optional[str] = None  # Only present on creation
    name: str
    user_id: Optional[int] = None
    permissions: Optional[str] = None
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None
    is_active: Optional[bool] = True

class CreateUserRequest(BaseModel):
    """Request to create user"""
    username: str
    password: str
    email: Optional[str] = None
    role: str = "user"

class UserResponse(BaseModel):
    """User response"""
    id: int
    username: str
    email: Optional[str] = None
    role: str
    created_at: Optional[str] = None
    is_active: Optional[bool] = True

class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    user: dict

# ========================================
# Params CRUD Models
# ========================================

class CreateParamRequest(BaseModel):
    """Request to create parameter"""
    key: str
    value: str
    description: Optional[str] = None
    category: Optional[str] = None

class UpdateParamRequest(BaseModel):
    """Request to update parameter"""
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None

class ParamResponse(BaseModel):
    """Parameter response"""
    id: int
    key: str
    value: str
    description: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

