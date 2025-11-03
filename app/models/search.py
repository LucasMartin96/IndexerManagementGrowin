"""
Search request and response models
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict


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
    divisaSimboloISO: Optional[str] = None
    tags: Optional[List[TagModel]] = None
    tag_ids: Optional[List[int]] = None
    mercado_ids: Optional[List[int]] = None
    tipo_licit_ids: Optional[Dict[str, Optional[int]]] = None
    tasaCambioUSD: Optional[float] = None
    pais_nombre: Optional[str] = None
    pais_id: Optional[int] = None
    vigente: Optional[bool] = None
    
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
        """Convert empty string or invalid monto to None, handle localized currency format"""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == '' or v == '0':
                return None
            # Handle localized currency format: remove '$', '.' and replace ',' with '.'
            if '$' in v:
                v = v.replace('$', '').replace('.', '').replace(',', '.')
            try:
                return float(v)
            except ValueError:
                return None
        try:
            return float(v) if v else None
        except (ValueError, TypeError):
            return None
    
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

