"""
Search endpoints - Gateway for PHP app
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.search import SearchLicitacionesRequest, SearchResponse, PublicationModel
from app.services.search_service import search_publications
from app.api.deps import allow_api_key

router = APIRouter()


@router.post("/search-licitaciones")  # Full path: /api/search-licitaciones
async def search_licitaciones(
    params: SearchLicitacionesRequest,
    current_auth: dict = Depends(allow_api_key)
):
    """
    Search publications in Elasticsearch
    Gateway endpoint for PHP application
    Access: JWT token or API key
    """
    try:
        # Convert Pydantic model to dict
        search_params = params.model_dump(exclude_none=True)
        
        # Search
        results = search_publications(search_params)
        
        # Convert publications to PublicationModel
        publications = []
        for pub_data in results.get('publicaciones', []):
            try:
                # Ensure array fields are lists
                tag_ids = pub_data.get('tag_ids') or []
                mercado_ids = pub_data.get('mercado_ids') or []
                
                # Remove tags from pub_data if present (handled separately)
                pub_data_copy = pub_data.copy()
                
                # Create PublicationModel
                publicacion = PublicationModel(**pub_data_copy)
                publications.append(publicacion)
            except Exception as e:
                # Log error but continue with other publications
                print(f"Error creating PublicationModel for pub {pub_data.get('id')}: {str(e)}")
                continue
        
        # Build response
        response = SearchResponse(
            publicaciones=publications,
            total=results.get('total', 0),
            pagina=results.get('pagina', 1),
            paginas=results.get('paginas', 1)
        )
        
        # Return with exclude_none=False to ensure all fields are included
        return response.model_dump(exclude_none=False)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

