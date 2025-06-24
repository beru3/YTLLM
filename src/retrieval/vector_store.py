import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import numpy as np
import hashlib

from src.utils.database import get_chroma_client, get_or_create_collection
from src.processing.embedding import generate_dummy_embedding, EMBEDDING_VECTOR_SIZE
from config.config import RETRIEVAL_TOP_K, HYBRID_ALPHA

logger = logging.getLogger(__name__)

def get_collection():
    """
    Get the ChromaDB collection.
    
    Returns:
        ChromaDB collection
    """
    client = get_chroma_client()
    return get_or_create_collection(client)

def add_chunks_to_vector_store(chunks: List[Dict[str, Any]]) -> None:
    """
    Add text chunks to the vector store.
    
    Args:
        chunks: List of text chunks with embeddings
    """
    if not chunks:
        return
    
    # Get ChromaDB client and collection
    client = get_chroma_client()
    collection = get_or_create_collection(client)
    
    # Extract data for ChromaDB
    ids = [chunk["vector_id"] for chunk in chunks]
    embeddings = [chunk.get("embedding") for chunk in chunks]
    texts = [chunk["text"] for chunk in chunks]
    
    # Prepare metadata
    metadatas = []
    for chunk in chunks:
        # Create a copy of the chunk without the text and embedding fields
        metadata = {k: v for k, v in chunk.items() if k not in ["text", "embedding"]}
        
        # Add source information
        if "video_id" in chunk:
            metadata["source_type"] = "video"
            metadata["source_id"] = chunk["video_id"]
            metadata["start_time"] = chunk.get("start_time", 0)
            metadata["end_time"] = chunk.get("end_time", 0)
        elif "document_id" in chunk:
            metadata["source_type"] = "document"
            metadata["source_id"] = chunk["document_id"]
            if "page" in chunk:
                metadata["page"] = chunk["page"]
            if "sheet_name" in chunk:
                metadata["sheet_name"] = chunk["sheet_name"]
        
        metadatas.append(metadata)
    
    # Add to collection
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )
    
    logger.info(f"Added {len(chunks)} chunks to vector store")

def search_vector_store(query: str, top_k: int = RETRIEVAL_TOP_K, alpha: float = HYBRID_ALPHA) -> List[Dict[str, Any]]:
    """
    Search the vector store for relevant chunks.
    
    Args:
        query: Search query
        top_k: Number of results to return
        alpha: Weight for hybrid search (0=BM25 only, 1=Vector only)
        
    Returns:
        List of relevant chunks with metadata
    """
    # Get ChromaDB client and collection
    client = get_chroma_client()
    collection = get_or_create_collection(client)
    
    try:
        # Generate dummy embedding for query to match the expected dimensionality
        query_embedding = generate_dummy_embedding(query)
        
        # Perform query with embedding
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.error(f"Error during vector search: {e}")
        # Fall back to keyword search
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
    
    # Format results
    chunks = []
    if results["documents"] and results["documents"][0]:
        for i, (doc, metadata, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            chunk = {
                "text": doc,
                "score": 1.0 - distance,  # Convert distance to similarity score
                "rank": i + 1
            }
            
            # Add metadata
            chunk.update(metadata)
            
            chunks.append(chunk)
    
    return chunks

def delete_chunks(vector_ids: List[str]) -> None:
    """
    Delete chunks from the vector store.
    
    Args:
        vector_ids: List of vector IDs to delete
    """
    if not vector_ids:
        return
    
    # Get ChromaDB client and collection
    client = get_chroma_client()
    collection = get_or_create_collection(client)
    
    # Delete from collection
    collection.delete(ids=vector_ids)
    
    logger.info(f"Deleted {len(vector_ids)} chunks from vector store") 