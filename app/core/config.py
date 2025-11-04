"""
Configuration from environment variables
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "case_sensitive": True}
    """Application settings from environment variables"""
    
    # Database Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_DATABASE: str = "growin_db"
    DB_USERNAME: str = "root"
    DB_PASSWORD: str = ""
    
    # Elasticsearch Configuration
    # ELASTICSEARCH_HOST can be:
    #   - Hostname/IP: "localhost" or "elasticsearch" (for docker) or "my-cluster.es.amazonaws.com"
    #   - Full URL: "https://my-cluster.es.amazonaws.com" or "http://elasticsearch:9200"
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_INDEX: str = "growin_licitaciones"
    ELASTICSEARCH_USERNAME: str | None = None
    ELASTICSEARCH_PASSWORD: str | None = None
    # Optional: Use API key instead of username/password
    # Format: "id:api_key" (e.g., "VuaCfGcBCdbkQm-e5aOx:ui2lp2axTNmsyakw9tvNnw")
    ELASTICSEARCH_API_KEY: str | None = None
    
    # FastAPI Configuration
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    
    # Scheduled Sync Configuration
    ELK_SYNC_HOUR: int = 3
    ELK_SYNC_MINUTE: int = 0
    
    # SQLite Configuration
    SQLITE_DB_PATH: str = "/app/data/elk_service.db"
    
    # Cleanup Configuration
    PROCESS_RETENTION_DAYS: int = 30  # Days to keep completed processes
    CLEANUP_INTERVAL_HOURS: int = 24  # Hours between cleanup runs (for future use)
    CLEANUP_RUN_HOUR: int = 2  # Hour of day to run cleanup (default 2 AM)
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS Configuration
    REACT_UI_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Note: "*" cannot be used with allow_credentials=True
        # For production, specify exact origins or use a wildcard subdomain pattern
    ]
    


# Global settings instance
settings = Settings()

