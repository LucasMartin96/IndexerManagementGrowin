"""
FastAPI Application Factory
Main application setup with startup/shutdown logic
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import atexit
from pathlib import Path

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db import (
    init_connection_pool,
    init_db as init_sqlite_db,
    initialize_elasticsearch
)
from app.api.v1.router import api_router
from app.utils.denormalize import denormalize_publication, get_publications_since
from app.api.v1.routes.indexer import set_executor
from app.api.v1.routes.processes import set_process_executor
from app.api.v1.routes.health import set_scheduler
from app.services.cleanup_service import run_cleanup

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Global scheduler
scheduler = AsyncIOScheduler()

# Global executor
executor = ThreadPoolExecutor(max_workers=10)


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    app = FastAPI(title="Growin ELK Service")
    
    # CORS middleware - MUST be added before any routes
    # Filter out invalid origins and ensure localhost:3000 is included
    cors_origins = [origin for origin in settings.CORS_ORIGINS if origin != "*"]
    if "http://localhost:3000" not in cors_origins:
        cors_origins.append("http://localhost:3000")
    if "http://127.0.0.1:3000" not in cors_origins:
        cors_origins.append("http://127.0.0.1:3000")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    logger.info(f"CORS configured for origins: {cors_origins}")
    
    # Add OPTIONS handler for CORS preflight
    @app.options("/{full_path:path}")
    async def options_handler(request: Request, full_path: str):
        """Handle CORS preflight requests"""
        origin = request.headers.get("origin")
        if origin in cors_origins:
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        return Response(status_code=403)
    
    # Include API router with prefix
    app.include_router(api_router, prefix="/api")
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize connections and start scheduler"""
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
        
        # Initialize Elasticsearch
        try:
            mapping_path = Path("es_mapping.json")
            if mapping_path.exists():
                with open(mapping_path, 'r') as f:
                    mapping = json.load(f)
                initialize_elasticsearch(mapping_file="es_mapping.json")
            else:
                logger.warning("es_mapping.json not found, creating index with default mapping")
                initialize_elasticsearch(mapping_file=None)
            
            logger.info("Elasticsearch connection established")
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch: {str(e)}")
            # Don't fail startup - allow service to start but endpoints will fail
        
        # Set executor for indexer routes
        set_executor(executor)
        set_process_executor(executor)
        
        # Set scheduler for health endpoint
        set_scheduler(scheduler)
        
        # Start scheduler for daily sync
        sync_hour = settings.ELK_SYNC_HOUR
        sync_minute = settings.ELK_SYNC_MINUTE
        
        scheduler.add_job(
            sync_all_publications,
            trigger=CronTrigger(hour=sync_hour, minute=sync_minute),
            id='daily_sync',
            name='Daily Sync All Publications',
            replace_existing=True
        )
        
        # Scheduled cleanup job
        cleanup_hour = settings.CLEANUP_RUN_HOUR
        scheduler.add_job(
            run_cleanup,
            trigger=CronTrigger(hour=cleanup_hour, minute=0),
            id='daily_cleanup',
            name='Daily Cleanup Old Processes',
            replace_existing=True
        )
        logger.info(f"Cleanup job scheduled to run daily at {cleanup_hour}:00")
        
        scheduler.start()
        logger.info(f"Scheduler started - Daily sync at {sync_hour:02d}:{sync_minute:02d}")
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Stop scheduler and cleanup on shutdown"""
        scheduler.shutdown()
        executor.shutdown(wait=False)
        logger.info("Scheduler stopped and executor shutdown")
    
    # Register shutdown with atexit as backup
    atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)
    
    return app


async def sync_all_publications():
    """
    Scheduled task - runs daily at configured hour
    Syncs all publications updated in last 24 hours
    """
    logger.info(f"Running scheduled sync at {datetime.now()}")
    
    from app.db import get_es_client
    from app.core.config import settings
    
    es_client = get_es_client()
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
                    es_client.index(index=settings.ELASTICSEARCH_INDEX, id=pub_id, document=doc)
                    indexed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to index publication {pub_id}: {str(e)}")
        
        logger.info(f"Scheduled sync completed: {indexed} indexed, {failed} failed")
        return {"status": "synced", "since": since_time, "indexed": indexed, "failed": failed}
        
    except Exception as e:
        logger.error(f"Scheduled sync failed: {str(e)}")
        return {"status": "error", "message": str(e)}


# Create app instance
app = create_app()

