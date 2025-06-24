#!/usr/bin/env python
import os
import logging
from src.utils.database import get_db_session, get_chroma_client, get_or_create_collection
from src.utils.models import Base
from config.config import SQLITE_PATH, CHROMA_DB_PATH
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database and vector store."""
    logger.info("Initializing database")
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    
    # Initialize SQLite database
    with get_db_session() as session:
        # Check if we can query
        try:
            session.execute(text("SELECT 1"))
            logger.info("SQLite database connection successful")
        except Exception as e:
            logger.error(f"SQLite database connection failed: {e}")
            return False
    
    # Initialize ChromaDB
    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        logger.info(f"ChromaDB initialized with collection: {collection.name}")
    except Exception as e:
        logger.error(f"ChromaDB initialization failed: {e}")
        return False
    
    logger.info("Database initialization completed successfully")
    return True

if __name__ == "__main__":
    init_database() 