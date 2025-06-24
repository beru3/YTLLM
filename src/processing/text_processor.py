import re
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
import json

from config.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and special characters.
    
    Args:
        text: Input text
        
    Returns:
        Cleaned text
    """
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that don't add meaning
    text = re.sub(r'[^\w\s\.,;:!?\'\"()\[\]\{\}]', '', text)
    
    return text.strip()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks of specified size with overlap.
    
    Args:
        text: Input text
        chunk_size: Maximum size of each chunk in characters
        overlap: Overlap between chunks in characters
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # If text is shorter than chunk_size, return it as a single chunk
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Find the end of the chunk
        end = start + chunk_size
        
        # If we're at the end of the text, just use the rest
        if end >= len(text):
            chunks.append(text[start:])
            break
        
        # Try to find a sentence boundary to break at
        sentence_end = text.rfind('. ', start, end)
        if sentence_end != -1:
            end = sentence_end + 1  # Include the period
        else:
            # If no sentence boundary, try to find a space
            space = text.rfind(' ', start, end)
            if space != -1:
                end = space
        
        # Add the chunk
        chunks.append(text[start:end].strip())
        
        # Move the start position for the next chunk, considering overlap
        start = end - overlap if end > overlap else end
    
    return chunks

def process_video_subtitles(subtitles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process video subtitles into chunks.
    
    Args:
        subtitles: List of subtitle segments
        
    Returns:
        List of text chunks with metadata
    """
    # Combine subtitles into a single text
    combined_text = " ".join([sub["text"] for sub in subtitles])
    
    # Clean the text
    cleaned_text = clean_text(combined_text)
    
    # Chunk the text
    text_chunks = chunk_text(cleaned_text)
    
    # Create chunk objects with metadata
    chunks = []
    
    # Calculate approximate character positions for each subtitle
    char_positions = []
    current_pos = 0
    for sub in subtitles:
        text_length = len(sub["text"])
        char_positions.append({
            "start": current_pos,
            "end": current_pos + text_length,
            "start_time": sub["start_time"],
            "end_time": sub["end_time"]
        })
        current_pos += text_length + 1  # +1 for the space we added between subtitles
    
    # Map each chunk to the appropriate time range
    total_text = " ".join([sub["text"] for sub in subtitles])
    current_pos = 0
    
    for i, chunk_text_content in enumerate(text_chunks):
        # Find the position of this chunk in the combined text
        chunk_start_pos = total_text.find(chunk_text_content, current_pos)
        if chunk_start_pos == -1:  # Fallback if exact match not found
            chunk_start_pos = current_pos
        chunk_end_pos = chunk_start_pos + len(chunk_text_content)
        current_pos = chunk_end_pos
        
        # Find the subtitles that overlap with this chunk
        overlapping_subs = [
            sub for sub in char_positions 
            if (sub["start"] <= chunk_end_pos and sub["end"] >= chunk_start_pos)
        ]
        
        if overlapping_subs:
            # Use the earliest start time and latest end time from overlapping subtitles
            chunk_start_time = min(sub["start_time"] for sub in overlapping_subs)
            chunk_end_time = max(sub["end_time"] for sub in overlapping_subs)
        else:
            # Fallback if no overlapping subtitles found
            chunk_start_time = subtitles[0]["start_time"] if subtitles else 0
            chunk_end_time = subtitles[-1]["end_time"] if subtitles else 0
        
        chunks.append({
            "text": chunk_text_content,
            "chunk_index": i,
            "start_time": chunk_start_time,
            "end_time": chunk_end_time,
            "vector_id": str(uuid.uuid4())
        })
    
    return chunks

def process_document_content(doc_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process document content into chunks.
    
    Args:
        doc_chunks: List of document chunks (e.g., PDF pages)
        
    Returns:
        List of text chunks with metadata
    """
    processed_chunks = []
    chunk_index = 0
    
    for doc_chunk in doc_chunks:
        # Clean the text
        cleaned_text = clean_text(doc_chunk["text"])
        
        # Chunk the text
        text_chunks = chunk_text(cleaned_text)
        
        # Create chunk objects with metadata
        for i, chunk_text_content in enumerate(text_chunks):
            metadata = {
                "text": chunk_text_content,
                "chunk_index": chunk_index,
                "vector_id": str(uuid.uuid4())
            }
            
            # Add document-specific metadata
            if "page" in doc_chunk:
                metadata["page"] = doc_chunk["page"]
            if "sheet_name" in doc_chunk:
                metadata["sheet_name"] = doc_chunk["sheet_name"]
                metadata["sheet_index"] = doc_chunk["sheet_index"]
            
            processed_chunks.append(metadata)
            chunk_index += 1
    
    return processed_chunks 