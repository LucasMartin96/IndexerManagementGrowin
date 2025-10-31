"""
Growin ELK FastAPI Service
Single service handling both indexing and querying
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import asyncio
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from models import (
    IndexLicitacionRequest,
    IndexScraperRequest,
    SyncSinceRequest,
    SearchLicitacionesRequest,
    IndexResponse,
    SearchResponse,
    HealthResponse,
    ErrorResponse,
    CreateAPIKeyRequest,
    APIKeyResponse,
    CreateUserRequest,
    UserResponse,
    LoginRequest,
    TokenResponse,
    CreateParamRequest,
    UpdateParamRequest,
    ParamResponse
)
from dependencies import (
    get_current_auth,
    require_full_access,
    allow_api_key
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Growin ELK Service")

# CORS middleware for PHP app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scheduler
scheduler = AsyncIOScheduler()

# ========================================
# IMPORTS
# ========================================
from denormalize import (
    denormalize_publication,
    get_publication_from_mysql,
    get_publications_from_scraper,
    get_publications_since,
    get_all_publication_ids
)
from database import mysql_connection, es_client_init, es_create_index, init_connection_pool
from database_sqlite import init_db as init_sqlite_db
import json

# Global connections
mysql_conn = None
es_client = None
ES_INDEX = os.getenv('ELASTICSEARCH_INDEX', 'growin_licitaciones')

# Thread pool for background tasks
executor = ThreadPoolExecutor(max_workers=10)

@app.on_event("startup")
async def startup_event():
    """Initialize connections and start scheduler"""
    global mysql_conn, es_client
    
    # Initialize MySQL connection pool
    try:
        init_connection_pool(max_connections=10)
        logger.info("MySQL connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MySQL connection pool: {str(e)}")
    
    # Initialize SQLite database
    try:
        init_sqlite_db()
        logger.info("SQLite database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {str(e)}")
    
    # Initialize Elasticsearch client
    try:
        es_client = es_client_init()
        
        # Load mapping and create index if needed
        try:
            with open('es_mapping.json', 'r') as f:
                mapping = json.load(f)
            es_create_index(es_client, ES_INDEX, mapping)
        except FileNotFoundError:
            logger.warning("es_mapping.json not found, creating index with default mapping")
            es_create_index(es_client, ES_INDEX)
        
        logger.info("Elasticsearch connection established")
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch: {str(e)}")
        # Don't fail startup - allow service to start but endpoints will fail
    
    # Start scheduler for daily sync
    sync_hour = int(os.getenv('ELK_SYNC_HOUR', '3'))
    sync_minute = int(os.getenv('ELK_SYNC_MINUTE', '0'))
    
    scheduler.add_job(
        sync_all_publications,
        trigger=CronTrigger(hour=sync_hour, minute=sync_minute),
        id='daily_sync',
        name='Daily Sync All Publications',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started - Daily sync at {sync_hour:02d}:{sync_minute:02d}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler and cleanup on shutdown"""
    scheduler.shutdown()
    executor.shutdown(wait=False)
    logger.info("Scheduler stopped and executor shutdown")

# Register shutdown with atexit as backup
atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)

# ========================================
# SCHEDULED TASKS
# ========================================

async def sync_all_publications():
    """
    Scheduled task - runs daily at configured hour
    Syncs all publications updated in last 24 hours
    """
    logger.info(f"Running scheduled sync at {datetime.now()}")
    
    if not es_client:
        logger.error("Elasticsearch client not initialized")
        return {"status": "error", "message": "Elasticsearch not available"}
    
    try:
        yesterday = datetime.now() - timedelta(days=1)
        since_time = yesterday.strftime('%Y-%m-%d %H:%M:%S')
        
        publication_ids = get_publications_since(since_time, limit=5000)
        
        indexed = 0
        failed = 0
        
        for pub_id in publication_ids:
            try:
                doc = denormalize_publication(pub_id)
                if doc:
                    es_client.index(index=ES_INDEX, id=pub_id, document=doc)
                    indexed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to index publication {pub_id}: {str(e)}")
        
        logger.info(f"Scheduled sync completed: {indexed} indexed, {failed} failed")
        return {"status": "synced", "since": since_time, "indexed": indexed, "failed": failed}
        
    except Exception as e:
        logger.error(f"Scheduled sync failed: {str(e)}")
        return {"status": "error", "message": str(e)}

# ========================================
# INDEXER ENDPOINTS
# ========================================

def _index_publication_sync(publicacion_id: int):
    """Synchronous function to index a publication (runs in background thread)"""
    try:
        if not es_client:
            logger.warning(f"Elasticsearch not available for publication {publicacion_id}")
            return
        
        doc = denormalize_publication(publicacion_id)
        if not doc:
            logger.warning(f"Publication {publicacion_id} not found")
            return
        
        es_client.index(index=ES_INDEX, id=publicacion_id, document=doc)
        logger.info(f"Indexed publication {publicacion_id}")
    except Exception as e:
        logger.error(f"Failed to index publication {publicacion_id}: {str(e)}")

@app.post("/api/index-licitacion", response_model=IndexResponse)
async def index_licitacion(
    request: IndexLicitacionRequest,
    current_auth: dict = Depends(allow_api_key)
) -> IndexResponse:
    """
    Index single publication by ID - webhook style (returns immediately, processes in background)
    Access: JWT token or API key
    """
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    # Schedule background task
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _index_publication_sync, request.publicacion_id)
    
    # Return immediately
    return IndexResponse(
        status="queued",
        id=request.publicacion_id,
        timestamp=datetime.now().isoformat()
    )

def _index_scraper_publications_sync(scraper_id: int, since: str):
    """Synchronous function to index scraper publications (runs in background thread)"""
    try:
        if not es_client:
            logger.warning("Elasticsearch not available - skipping indexing")
            return
        
        publication_ids = get_publications_from_scraper(scraper_id, since, limit=1000)
        
        indexed = 0
        failed = 0
        
        for pub_id in publication_ids:
            try:
                doc = denormalize_publication(pub_id)
                if doc:
                    es_client.index(index=ES_INDEX, id=pub_id, document=doc)
                    indexed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to index publication {pub_id}: {str(e)}")
        
        logger.info(f"Indexed {indexed} publications from scraper {scraper_id} since {since}")
    except Exception as e:
        logger.error(f"Failed to index scraper publications: {str(e)}")

@app.post("/api/index-scraper-publications", response_model=IndexResponse)
async def index_scraper_publications(
    request: IndexScraperRequest,
    current_auth: dict = Depends(allow_api_key)
) -> IndexResponse:
    """
    Index all publications from a scraper since given time - webhook style (returns immediately)
    Access: JWT token or API key
    """
    if not es_client:
        logger.warning("Elasticsearch not available - skipping indexing")
        return IndexResponse(status="error", message="Elasticsearch not available")
    
    # Schedule background task
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _index_scraper_publications_sync, request.scraper_id, request.since)
    
    # Return immediately
    return IndexResponse(
        status="queued",
        scraper_id=request.scraper_id,
        since=request.since,
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/index-bulk", response_model=IndexResponse)
async def index_bulk(
    current_user: dict = Depends(require_full_access)
) -> IndexResponse:
    """
    Initial bulk index - index all publications
    Processes in batches of 1000
    Access: JWT token only (full access required)
    """
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    try:
        batch_size = 1000
        offset = 0
        total_indexed = 0
        total_failed = 0
        
        logger.info("Starting bulk indexing...")
        
        while True:
            publication_ids = get_all_publication_ids(batch_size, offset)
            
            if not publication_ids:
                break
            
            # Bulk index this batch
            actions = []
            
            for pub_id in publication_ids:
                try:
                    doc = denormalize_publication(pub_id)
                    if doc:
                        actions.append({
                            "_index": ES_INDEX,
                            "_id": pub_id,
                            "_source": doc
                        })
                except Exception as e:
                    total_failed += 1
                    logger.error(f"Failed to denormalize publication {pub_id}: {str(e)}")
            
            # Bulk insert
            if actions:
                try:
                    from elasticsearch.helpers import streaming_bulk
                    success_count = 0
                    for ok, response in streaming_bulk(es_client, actions, chunk_size=500):
                        if ok:
                            success_count += 1
                        else:
                            total_failed += 1
                    total_indexed += success_count
                except Exception as e:
                    logger.error(f"Bulk insert failed: {str(e)}")
                    total_failed += len(actions)
            
            offset += batch_size
            
            logger.info(f"Bulk indexing progress: {offset} processed, {total_indexed} indexed")
        
        logger.info(f"Bulk indexing completed: {total_indexed} indexed, {total_failed} failed")
        return IndexResponse(
            status="indexed",
            total_indexed=total_indexed,
            total_failed=total_failed
        )
        
    except Exception as e:
        logger.error(f"Bulk indexing failed: {str(e)}")
        return IndexResponse(status="error", message=str(e))

def _sync_since_sync(since: str):
    """Synchronous function to sync publications since date (runs in background thread)"""
    try:
        if not es_client:
            logger.warning("Elasticsearch not available - skipping sync")
            return
        
        publication_ids = get_publications_since(since, limit=5000)
        
        indexed = 0
        failed = 0
        
        for pub_id in publication_ids:
            try:
                doc = denormalize_publication(pub_id)
                if doc:
                    es_client.index(index=ES_INDEX, id=pub_id, document=doc)
                    indexed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to index publication {pub_id}: {str(e)}")
        
        logger.info(f"Sync completed since {since}: {indexed} indexed, {failed} failed")
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")

@app.post("/api/sync-since", response_model=IndexResponse)
async def sync_since(
    request: SyncSinceRequest,
    current_user: dict = Depends(require_full_access)
) -> IndexResponse:
    """
    Sync publications updated since given date - webhook style (returns immediately)
    Access: JWT token only (full access required)
    """
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    # Schedule background task
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _sync_since_sync, request.since)
    
    # Return immediately
    return IndexResponse(
        status="queued",
        since=request.since,
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/trigger-sync", response_model=IndexResponse)
async def trigger_sync() -> IndexResponse:
    """
    Manually trigger daily sync (for testing)
    """
    result = await sync_all_publications()
    # Convert dict result to IndexResponse if needed
    if isinstance(result, dict):
        return IndexResponse(**result)
    return result

# ========================================
# GATEWAY ENDPOINTS
# ========================================

@app.post("/api/search-licitaciones")
async def search_licitaciones(
    params: SearchLicitacionesRequest,
    current_auth: dict = Depends(allow_api_key)
):
    """
    Query Elasticsearch - receives params from PHP
    Pure gateway - no business logic
    Access: JWT token or API key
    """
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    try:
        from query_builder import build_es_query, format_es_results
        
        # Convert request model to dict for query builder
        params_dict = params.model_dump(exclude_none=True)
        
        # Build Elasticsearch query from PHP params
        es_query_dsl = build_es_query(params_dict)
        
        # Pagination
        from_offset = (params.page - 1) * params.page_size
        
        # Sorting
        sort = [
            {"editado": {"order": "desc"}},
            {"id": {"order": "desc"}}
        ]
        
        # Execute Elasticsearch query
        es_query = {
            "query": es_query_dsl,
            "from": from_offset,
            "size": params.page_size,
            "sort": sort
        }
        
        results = es_client.search(index=ES_INDEX, body=es_query)
        
        # Format results to match MySQL response
        formatted_results = format_es_results(results, params_dict)
        
        # Convert to SearchResponse model
        from models import PublicationModel, TagModel
        
        publicaciones = []
        for pub in formatted_results.get('publicaciones', []):
            # Extract and convert tags if present
            pub_data = pub.copy()  # Make a copy to avoid modifying original
            
            # Ensure arrays are lists (not None)
            if 'tag_ids' in pub_data and not pub_data['tag_ids']:
                pub_data['tag_ids'] = []
            if 'mercado_ids' in pub_data and not pub_data['mercado_ids']:
                pub_data['mercado_ids'] = []
            
            # Convert tags array if present
            tags = None
            if 'tags' in pub_data:
                if pub_data['tags']:
                    tags_data = pub_data.pop('tags')
                    tags = [TagModel(**tag) if isinstance(tag, dict) else tag for tag in tags_data]
                else:
                    pub_data.pop('tags')
                    tags = []
            
            # Create PublicationModel - it will handle all fields including arrays
            try:
                publicacion = PublicationModel(**pub_data)
                # Set tags after creation if needed
                if tags is not None:
                    publicacion.tags = tags if tags else []
            except Exception as e:
                logger.error(f"Error creating PublicationModel: {str(e)}, data: {pub_data.keys()}")
                raise
            
            publicaciones.append(publicacion)
        
        response = SearchResponse(
            publicaciones=publicaciones,
            total=formatted_results.get('total', 0),
            pagina=formatted_results.get('pagina', 1),
            paginas=formatted_results.get('paginas', 1)
        )
        
        # Use model_dump with exclude_none=False to include all fields like before
        return response.model_dump(exclude_none=False)
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
        scheduler_running=scheduler.running
    )

# ========================================
# AUTH ENDPOINTS
# ========================================

@app.post("/api/auth/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    request: CreateAPIKeyRequest,
    current_user: dict = Depends(require_full_access)
) -> APIKeyResponse:
    """
    Create a new API key
    Returns the plaintext key only once - save it!
    Access: JWT token only (full access required)
    """
    from auth import create_api_key
    
    # If user_id not provided, use current user
    user_id = request.user_id or current_user.get('id')
    
    key_data = create_api_key(
        name=request.name,
        user_id=user_id,
        permissions=request.permissions,
        expires_days=request.expires_days
    )
    
    return APIKeyResponse(**key_data)

@app.get("/api/auth/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys_endpoint(
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_full_access)
) -> List[APIKeyResponse]:
    """
    List all API keys (without plaintext keys)
    Access: JWT token only (full access required)
    """
    from auth import list_api_keys
    
    # If user_id not provided, filter by current user
    if not user_id:
        user_id = current_user.get('id')
    
    keys = list_api_keys(user_id=user_id)
    return [APIKeyResponse(**key) for key in keys]

@app.delete("/api/auth/api-keys/{key_id}")
async def revoke_api_key_endpoint(
    key_id: int,
    current_user: dict = Depends(require_full_access)
) -> dict:
    """
    Revoke an API key
    Access: JWT token only (full access required)
    """
    from auth import revoke_api_key
    
    success = revoke_api_key(key_id)
    if success:
        return {"status": "revoked", "key_id": key_id}
    raise HTTPException(status_code=404, detail="API key not found")

@app.post("/api/auth/login", response_model=TokenResponse)
async def login_endpoint(request: LoginRequest) -> TokenResponse:
    """Login and get JWT token"""
    from auth import verify_user, create_access_token
    
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

@app.post("/api/auth/users", response_model=UserResponse)
async def create_user_endpoint(
    request: CreateUserRequest,
    current_user: dict = Depends(require_full_access)
) -> UserResponse:
    """
    Create a new user
    Access: JWT token only (full access required)
    """
    from auth import create_user
    
    user = create_user(
        username=request.username,
        password=request.password,
        email=request.email,
        role=request.role
    )
    
    return UserResponse(**user)

# ========================================
# PARAMS CRUD ENDPOINTS
# ========================================

@app.post("/api/params", response_model=ParamResponse)
async def create_param_endpoint(
    request: CreateParamRequest,
    current_user: dict = Depends(require_full_access)
) -> ParamResponse:
    """
    Create a new parameter
    Access: JWT token only (full access required)
    """
    from crud import create_param
    
    param = create_param(
        key=request.key,
        value=request.value,
        description=request.description,
        category=request.category
    )
    
    return ParamResponse(**param)

@app.get("/api/params/{key}", response_model=ParamResponse)
async def get_param_endpoint(
    key: str,
    current_user: dict = Depends(require_full_access)
) -> ParamResponse:
    """
    Get parameter by key
    Access: JWT token only (full access required)
    """
    from crud import get_param
    
    param = get_param(key)
    if not param:
        raise HTTPException(status_code=404, detail=f"Parameter '{key}' not found")
    
    return ParamResponse(**param)

@app.put("/api/params/{key}", response_model=ParamResponse)
async def update_param_endpoint(
    key: str,
    request: UpdateParamRequest,
    current_user: dict = Depends(require_full_access)
) -> ParamResponse:
    """
    Update parameter by key
    Access: JWT token only (full access required)
    """
    from crud import update_param, get_param
    
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

@app.delete("/api/params/{key}")
async def delete_param_endpoint(
    key: str,
    current_user: dict = Depends(require_full_access)
) -> dict:
    """
    Delete parameter by key
    Access: JWT token only (full access required)
    """
    from crud import delete_param as delete_param_crud
    
    success = delete_param_crud(key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Parameter '{key}' not found")
    
    return {"status": "deleted", "key": key}

@app.get("/api/params", response_model=List[ParamResponse])
async def list_params_endpoint(
    category: Optional[str] = None,
    current_user: dict = Depends(require_full_access)
) -> List[ParamResponse]:
    """
    List all parameters
    Access: JWT token only (full access required)
    """
    from crud import list_params
    
    params = list_params(category=category)
    return [ParamResponse(**param) for param in params]

@app.get("/api/params/search/{search_term}", response_model=List[ParamResponse])
async def search_params_endpoint(
    search_term: str,
    current_user: dict = Depends(require_full_access)
) -> List[ParamResponse]:
    """
    Search parameters
    Access: JWT token only (full access required)
    """
    from crud import search_params
    
    params = search_params(search_term)
    return [ParamResponse(**param) for param in params]

@app.get("/api/params/categories/list", response_model=List[str])
async def get_categories_endpoint(
    current_user: dict = Depends(require_full_access)
) -> List[str]:
    """
    Get all categories
    Access: JWT token only (full access required)
    """
    from crud import get_categories
    
    return get_categories()

@app.get("/api/params/category/{category}", response_model=List[ParamResponse])
async def get_params_by_category_endpoint(
    category: str,
    current_user: dict = Depends(require_full_access)
) -> List[ParamResponse]:
    """
    Get parameters by category
    Access: JWT token only (full access required)
    """
    from crud import get_params_by_category
    
    params = get_params_by_category(category)
    return [ParamResponse(**param) for param in params]

if __name__ == "__main__":
    import uvicorn
    host = os.getenv('FASTAPI_HOST', '0.0.0.0')
    port = int(os.getenv('FASTAPI_PORT', '8000'))
    uvicorn.run(app, host=host, port=port)

