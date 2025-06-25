import logging
import os
from typing import List, Dict, Any
from pathlib import Path

from src.utils.database import get_db_session
from src.utils.models import Video, Subtitle, TextChunk
from src.processing.text_processor import process_video_subtitles
from src.processing.embedding import generate_embeddings, store_embeddings
from src.retrieval.vector_store import add_chunks_to_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def rebuild_vector_store():
    """
    Rebuild the vector store with existing video subtitles.
    """
    logger.info("Starting vector store rebuild")
    
    # Get all videos with subtitles
    with get_db_session() as session:
        videos = session.query(Video).filter(Video.subtitles.any()).all()
        logger.info(f"Found {len(videos)} videos with subtitles")
        
        for i, video in enumerate(videos):
            logger.info(f"Processing video {i+1}/{len(videos)}: {video.title}")
            
            # Get subtitle text
            subtitles = session.query(Subtitle).filter(Subtitle.video_id == video.id).all()
            if not subtitles:
                logger.warning(f"No subtitles for video {video.id}")
                continue
            
            # Process subtitles into chunks
            subtitle_data_list = []
            for subtitle in subtitles:
                subtitle_data = {
                    "video_id": video.id,
                    "text": subtitle.text,
                    "language": subtitle.language,
                    "start_time": subtitle.start_time,
                    "end_time": subtitle.end_time
                }
                subtitle_data_list.append(subtitle_data)
            
            chunks = process_video_subtitles(subtitle_data_list)
            
            # Add video_id to chunks
            for chunk in chunks:
                chunk["video_id"] = video.id
            
            if not chunks:
                logger.warning(f"No chunks generated for video {video.id}")
                continue
            
            # Generate embeddings
            texts = [chunk["text"] for chunk in chunks]
            embeddings = generate_embeddings(texts)
            
            # Store embeddings in chunks
            chunks_with_embeddings = store_embeddings(chunks, embeddings)
            
            # Add to vector store
            add_chunks_to_vector_store(chunks_with_embeddings)
            
            # Update text chunks in database
            existing_chunks = session.query(TextChunk).filter(TextChunk.video_id == video.id).all()
            for chunk in existing_chunks:
                session.delete(chunk)
            
            for chunk in chunks_with_embeddings:
                text_chunk = TextChunk(
                    text=chunk["text"],
                    video_id=chunk["video_id"],
                    chunk_index=chunk["chunk_index"],
                    vector_id=chunk["vector_id"],
                    start_time=chunk.get("start_time", 0),
                    end_time=chunk.get("end_time", 0)
                )
                session.add(text_chunk)
            
            # Commit after each video to avoid losing progress
            session.commit()
            
            logger.info(f"Added {len(chunks)} chunks for video {video.id}")
    
    logger.info("Vector store rebuild completed")

if __name__ == "__main__":
    rebuild_vector_store() 