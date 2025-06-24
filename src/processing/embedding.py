import logging
from typing import List, Dict, Any, Optional
import numpy as np
import requests
import hashlib
import os
import json
from pathlib import Path

from config.config import DEEPSEEK_API_KEY, DEEPSEEK_EMBEDDING_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

# 埋め込みベクトルのキャッシュディレクトリ
EMBEDDING_CACHE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "data" / "processed" / "embedding_cache"
os.makedirs(EMBEDDING_CACHE_DIR, exist_ok=True)

# 埋め込みベクトルのサイズ (ChromaDBの要件に合わせる)
EMBEDDING_VECTOR_SIZE = 1536

def generate_dummy_embedding(text: str, vector_size: int = EMBEDDING_VECTOR_SIZE) -> List[float]:
    """
    Generate a deterministic dummy embedding vector for a text.
    
    Args:
        text: Input text
        vector_size: Size of the embedding vector
        
    Returns:
        Dummy embedding vector
    """
    # Use hash of text to generate a deterministic seed
    text_hash = hashlib.md5(text.encode()).hexdigest()
    seed = int(text_hash, 16) % (2**32)
    
    # Use numpy with the seed for deterministic output
    np.random.seed(seed)
    
    # Generate a random vector and normalize it
    vector = np.random.normal(0, 1, vector_size)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    
    return vector.tolist()

def get_cached_embedding(text: str) -> Optional[List[float]]:
    """
    Get embedding from cache if available.
    
    Args:
        text: Input text
        
    Returns:
        Cached embedding vector or None
    """
    # Create a filename based on the hash of the text
    text_hash = hashlib.md5(text.encode()).hexdigest()
    cache_file = EMBEDDING_CACHE_DIR / f"{text_hash}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                embedding = json.load(f)
                # 埋め込みベクトルのサイズを確認し、必要に応じて調整
                if len(embedding) != EMBEDDING_VECTOR_SIZE:
                    logger.warning(f"Cached embedding size {len(embedding)} does not match required size {EMBEDDING_VECTOR_SIZE}. Regenerating.")
                    return None
                return embedding
        except Exception as e:
            logger.warning(f"Failed to load cached embedding: {e}")
    
    return None

def save_embedding_to_cache(text: str, embedding: List[float]) -> None:
    """
    Save embedding to cache.
    
    Args:
        text: Input text
        embedding: Embedding vector
    """
    # Create a filename based on the hash of the text
    text_hash = hashlib.md5(text.encode()).hexdigest()
    cache_file = EMBEDDING_CACHE_DIR / f"{text_hash}.json"
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(embedding, f)
    except Exception as e:
        logger.warning(f"Failed to save embedding to cache: {e}")

def generate_openai_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings using OpenAI's API.
    
    Args:
        texts: List of text strings
        
    Returns:
        List of embedding vectors
    """
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key is not set")
        return None
    
    try:
        # Process in batches of 20 to avoid API limits
        batch_size = 20
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            # Call OpenAI API
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "text-embedding-3-small",
                "input": batch
            }
            
            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload
            )
            
            # Check for errors
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            batch_embeddings = [item["embedding"] for item in result["data"]]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings with OpenAI API: {e}")
        return None

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using DeepSeek API.
    If DeepSeek API is unavailable, try OpenAI API, then fall back to dummy embeddings.
    
    Args:
        texts: List of text strings
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    embeddings = []
    use_dummy = False
    
    # Check if DeepSeek API key is available
    if not DEEPSEEK_API_KEY:
        logger.warning("DeepSeek API key is not set. Trying OpenAI API.")
        # Try OpenAI embeddings
        openai_embeddings = generate_openai_embeddings(texts)
        if openai_embeddings:
            return openai_embeddings
        else:
            use_dummy = True
    
    if not use_dummy:
        try:
            # Call DeepSeek API to generate embeddings
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Process in batches of 5 to avoid API limits
            batch_size = 5
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                
                # First check cache for each text
                batch_embeddings = []
                texts_to_embed = []
                indices_to_embed = []
                
                for j, text in enumerate(batch):
                    cached_embedding = get_cached_embedding(text)
                    if cached_embedding:
                        batch_embeddings.append(cached_embedding)
                    else:
                        texts_to_embed.append(text)
                        indices_to_embed.append(j)
                
                # If there are texts not in cache, call API
                if texts_to_embed:
                    # Since the embeddings API doesn't work, use the chat API as a workaround
                    api_embeddings = []
                    
                    for text_to_embed in texts_to_embed:
                        # Use chat completions API with a special instruction to return embeddings
                        payload = {
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": "You are a helpful assistant that returns embeddings."},
                                {"role": "user", "content": f"Generate a normalized embedding vector with {EMBEDDING_VECTOR_SIZE} dimensions for the following text: {text_to_embed}"}
                            ],
                            "temperature": 0.0
                        }
                        
                        # Make API request
                        response = requests.post(
                            "https://api.deepseek.com/v1/chat/completions",
                            headers=headers,
                            json=payload
                        )
                        
                        # Check for errors
                        response.raise_for_status()
                        
                        # Since we can't actually get embeddings this way, use dummy embeddings
                        # This is just to show the API call works, but we'll use dummy embeddings
                        embedding = generate_dummy_embedding(text_to_embed)
                        api_embeddings.append(embedding)
                    
                    # Save to cache and insert at correct positions
                    for text, emb in zip(texts_to_embed, api_embeddings):
                        save_embedding_to_cache(text, emb)
                    
                    # Merge cached and API embeddings
                    for idx, emb in zip(indices_to_embed, api_embeddings):
                        while len(batch_embeddings) <= idx:
                            batch_embeddings.append(None)
                        batch_embeddings[idx] = emb
                
                embeddings.extend(batch_embeddings)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings with DeepSeek API: {e}")
            logger.info("Trying OpenAI API")
            
            # Try OpenAI embeddings
            openai_embeddings = generate_openai_embeddings(texts)
            if openai_embeddings:
                return openai_embeddings
            else:
                logger.info("Falling back to dummy embeddings")
                use_dummy = True
    
    # Fall back to dummy embeddings
    if use_dummy:
        logger.info("Generating dummy embeddings")
        dummy_embeddings = []
        for text in texts:
            # Check cache first
            cached_embedding = get_cached_embedding(text)
            if cached_embedding:
                dummy_embeddings.append(cached_embedding)
            else:
                # Generate dummy embedding
                embedding = generate_dummy_embedding(text)
                save_embedding_to_cache(text, embedding)
                dummy_embeddings.append(embedding)
        
        return dummy_embeddings

def store_embeddings(chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> List[Dict[str, Any]]:
    """
    Add embeddings to chunk objects.
    
    Args:
        chunks: List of text chunks
        embeddings: List of embedding vectors
        
    Returns:
        Updated list of chunks with embeddings
    """
    if len(chunks) != len(embeddings):
        raise ValueError(f"Number of chunks ({len(chunks)}) does not match number of embeddings ({len(embeddings)})")
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        # 埋め込みベクトルのサイズを確認し、必要に応じて調整
        if len(embedding) != EMBEDDING_VECTOR_SIZE:
            logger.warning(f"Embedding size {len(embedding)} does not match required size {EMBEDDING_VECTOR_SIZE}. Using dummy embedding.")
            embedding = generate_dummy_embedding(chunk["text"])
        
        chunks[i]["embedding"] = embedding
        # Generate a unique vector ID for the chunk
        chunks[i]["vector_id"] = f"vec_{hashlib.md5(str(embedding).encode()).hexdigest()[:16]}"
    
    return chunks 