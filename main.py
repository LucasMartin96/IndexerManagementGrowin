"""
Main entry point - imports from app.main
This file maintains backward compatibility and is the entry point for uvicorn
"""

import uvicorn
import os
from app.main import app

if __name__ == "__main__":
    host = os.getenv('FASTAPI_HOST', '0.0.0.0')
    port = int(os.getenv('FASTAPI_PORT', '8000'))
    uvicorn.run(app, host=host, port=port)
