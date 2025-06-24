import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import chromadb
from chromadb.config import Settings

from src.utils.models import Base
from config.config import SQLITE_PATH, CHROMA_DB_PATH

# Ensure directories exist
os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
os.makedirs(CHROMA_DB_PATH, exist_ok=True)

# SQLite database engine
engine = create_engine(f"sqlite:///{SQLITE_PATH}", connect_args={"check_same_thread": False})

# Create all tables
Base.metadata.create_all(engine)

# Session factory
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# ChromaDB client
def get_chroma_client():
    """Get or create a ChromaDB client."""
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    return client

def get_or_create_collection(client, collection_name="marketing_knowledge"):
    """Get or create a ChromaDB collection."""
    try:
        collection = client.get_collection(collection_name)
    except ValueError:
        # Collection doesn't exist, create it
        collection = client.create_collection(
            name=collection_name,
            metadata={"description": "Marketing knowledge from YouTube videos and documents"}
        )
    return collection 