#!/usr/bin/env python
import os
import logging
import time
from datetime import datetime, timedelta
import json

from src.ingestion.ingest import ingest_channel, update_video_subtitles
from src.utils.database import get_db_session
from src.utils.models import Video, TextChunk, Subtitle
from src.processing.text_processor import process_video_subtitles
from src.processing.embedding import generate_embeddings, store_embeddings
from src.retrieval.vector_store import add_chunks_to_vector_store

from config.config import YOUTUBE_CHANNEL_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def batch_update():
    """
    Run a batch update to ingest new videos from the channel.
    """
    logger.info("Starting batch update")
    
    # Get the latest video date from the database
    latest_video_date = None
    with get_db_session() as session:
        latest_video = session.query(Video).order_by(Video.published_at.desc()).first()
        if latest_video:
            latest_video_date = latest_video.published_at
    
    if latest_video_date:
        logger.info(f"Latest video in database is from {latest_video_date}")
    else:
        logger.info("No videos in database, will ingest all videos")
    
    # Run the ingestion
    try:
        ingest_channel(YOUTUBE_CHANNEL_ID)
    except Exception as e:
        logger.error(f"Batch update failed: {e}", exc_info=True)
        return False
    
    # Log success
    logger.info("Batch update completed successfully")
    
    # Record the update time
    with open("data/last_update.json", "w") as f:
        json.dump({
            "last_update": datetime.utcnow().isoformat(),
            "status": "success"
        }, f)
    
    return True

def update_all_videos_with_accurate_timestamps(max_videos: int = None):
    """
    Update all existing videos with accurate timestamps for their text chunks.
    This function reprocesses the subtitles to create chunks with more accurate time ranges.
    
    Args:
        max_videos: Maximum number of videos to update (None for all)
    """
    logger.info("Starting update of all videos with accurate timestamps")
    
    # Get all videos with existing subtitles
    with get_db_session() as session:
        # Find videos with subtitles
        videos_with_subtitles = session.query(Video.id).join(Video.subtitles).group_by(Video.id).all()
        video_ids = [v[0] for v in videos_with_subtitles]
        
        if max_videos:
            video_ids = video_ids[:max_videos]
        
        logger.info(f"Found {len(video_ids)} videos to update with accurate timestamps")
    
    # Update each video
    for i, video_id in enumerate(video_ids):
        try:
            logger.info(f"Updating timestamps for video {i+1}/{len(video_ids)}: {video_id}")
            
            # Get existing subtitles
            with get_db_session() as session:
                subtitle_records = session.query(Subtitle).filter(Subtitle.video_id == video_id).all()
                subtitles = [
                    {
                        "start_time": sub.start_time,
                        "end_time": sub.end_time,
                        "text": sub.text,
                        "is_auto_generated": sub.is_auto_generated,
                        "language": sub.language
                    }
                    for sub in subtitle_records
                ]
            
            if not subtitles:
                logger.warning(f"No subtitles found for video {video_id}, skipping")
                continue
            
            # Process subtitles into chunks with accurate timestamps
            chunks = process_video_subtitles(subtitles)
            
            # Add video_id to chunks
            for chunk in chunks:
                chunk["video_id"] = video_id
            
            # Generate embeddings
            texts = [chunk["text"] for chunk in chunks]
            embeddings = generate_embeddings(texts)
            
            # Store embeddings in chunks
            chunks_with_embeddings = store_embeddings(chunks, embeddings)
            
            # Store chunks in vector store
            add_chunks_to_vector_store(chunks_with_embeddings)
            
            # Store chunks in database
            with get_db_session() as session:
                # Delete existing chunks if any
                session.query(TextChunk).filter(TextChunk.video_id == video_id).delete()
                
                # Add new chunks
                for chunk in chunks_with_embeddings:
                    text_chunk = TextChunk(
                        text=chunk["text"],
                        video_id=chunk["video_id"],
                        chunk_index=chunk["chunk_index"],
                        start_time=chunk.get("start_time"),
                        end_time=chunk.get("end_time"),
                        vector_id=chunk["vector_id"]
                    )
                    session.add(text_chunk)
            
            logger.info(f"Successfully updated timestamps for video {video_id}")
            
            # Sleep to avoid overloading the system
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to update timestamps for video {video_id}: {e}", exc_info=True)
    
    logger.info("Completed updating all videos with accurate timestamps")
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run batch update for video ingestion")
    parser.add_argument("--update-timestamps", action="store_true", help="Update all videos with accurate timestamps")
    parser.add_argument("--max", type=int, help="Maximum number of videos to process")
    
    args = parser.parse_args()
    
    if args.update_timestamps:
        update_all_videos_with_accurate_timestamps(args.max)
    else:
        batch_update() 