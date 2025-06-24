import os
import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text

from src.ingestion.youtube import (
    get_channel_videos,
    get_video_details,
    get_video_subtitles,
    format_video_data
)
from src.ingestion.whisper_transcription import transcribe_video
from src.ingestion.document_processor import process_document
from src.processing.text_processor import process_video_subtitles, process_document_content
from src.processing.embedding import generate_embeddings, store_embeddings
from src.retrieval.vector_store import add_chunks_to_vector_store
from src.utils.database import get_db_session
from src.utils.models import Video, Subtitle, Document, TextChunk

from config.config import YOUTUBE_CHANNEL_ID, USE_DEEPSEEK

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def ingest_video(video_id: str, force_transcribe: bool = False) -> None:
    """
    Ingest a single video.
    
    Args:
        video_id: YouTube video ID
        force_transcribe: Force transcription even if subtitles exist
    """
    logger.info(f"Ingesting video {video_id}")
    
    # Get video details
    video_details = get_video_details([video_id])
    if not video_details:
        logger.error(f"Failed to get details for video {video_id}")
        return
    
    # Format video data
    video_data = format_video_data(video_details[0])
    
    # Store video metadata in database
    with get_db_session() as session:
        # Check if video already exists
        existing_video = session.query(Video).filter(Video.id == video_id).first()
        if existing_video:
            logger.info(f"Video {video_id} already exists, updating metadata")
            
            # Update metadata
            for key, value in video_data.items():
                setattr(existing_video, key, value)
            
            video = existing_video
        else:
            logger.info(f"Creating new video record for {video_id}")
            
            # Create new video
            video = Video(**video_data)
            session.add(video)
            session.flush()  # Flush to get the ID
    
    # Get subtitles
    subtitles = get_video_subtitles(video_id)
    
    # If no subtitles or force_transcribe, use Whisper or DeepSeek
    if not subtitles or force_transcribe:
        if USE_DEEPSEEK:
            logger.info(f"No subtitles found or force_transcribe=True, using DeepSeek for {video_id}")
            # DeepSeekを使用する場合は、字幕をテキスト化して処理
            # 注：実際のDeepSeek APIを使った処理はここに実装する必要がありますが、
            # 今回は簡単な例として、タイトルとIDをテキストとして使用します
            subtitles = [{
                "start_time": 0,
                "end_time": video_data.get("duration_seconds", 0),
                "text": f"Video title: {video_data.get('title', '')}. Video ID: {video_id}",
                "is_auto_generated": True,
                "language": "ja"
            }]
        else:
            logger.info(f"No subtitles found or force_transcribe=True, using Whisper for {video_id}")
            subtitles = transcribe_video(video_id)
    
    # Store subtitles in database
    with get_db_session() as session:
        # Delete existing subtitles if any
        session.query(Subtitle).filter(Subtitle.video_id == video_id).delete()
        
        # Add new subtitles
        for sub in subtitles:
            subtitle = Subtitle(
                video_id=video_id,
                start_time=sub["start_time"],
                end_time=sub["end_time"],
                text=sub["text"],
                is_auto_generated=sub.get("is_auto_generated", False),
                language=sub.get("language", "ja")
            )
            session.add(subtitle)
    
    # Process subtitles into chunks
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
    
    logger.info(f"Successfully ingested video {video_id}")

def update_video_subtitles(video_id: str) -> None:
    """
    Update subtitles for a video, replacing placeholders with actual subtitles.
    
    Args:
        video_id: YouTube video ID
    """
    logger.info(f"Updating subtitles for video {video_id}")
    
    # Check if video exists in database
    with get_db_session() as session:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found in database")
            return
        
        # Check if subtitles are placeholders
        subtitles = session.query(Subtitle).filter(Subtitle.video_id == video_id).all()
        is_placeholder = any(sub.text.startswith("Subtitles would be downloaded here for") for sub in subtitles)
        
        if not is_placeholder and subtitles:
            logger.info(f"Video {video_id} already has non-placeholder subtitles, skipping")
            return
    
    # Get actual subtitles
    new_subtitles = get_video_subtitles(video_id)
    
    if not new_subtitles:
        logger.warning(f"Could not retrieve subtitles for video {video_id}")
        return
    
    logger.info(f"Retrieved {len(new_subtitles)} subtitle segments for video {video_id}")
    
    # Store new subtitles in database
    with get_db_session() as session:
        # Delete existing subtitles
        session.query(Subtitle).filter(Subtitle.video_id == video_id).delete()
        
        # Add new subtitles
        for sub in new_subtitles:
            subtitle = Subtitle(
                video_id=video_id,
                start_time=sub["start_time"],
                end_time=sub["end_time"],
                text=sub["text"],
                is_auto_generated=sub.get("is_auto_generated", False),
                language=sub.get("language", "ja")
            )
            session.add(subtitle)
    
    # Process subtitles into chunks
    chunks = process_video_subtitles(new_subtitles)
    
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
    
    logger.info(f"Successfully updated subtitles and chunks for video {video_id}")

def update_all_placeholder_subtitles(max_videos: int = None) -> None:
    """
    Update all videos with placeholder subtitles.
    
    Args:
        max_videos: Maximum number of videos to update (None for all)
    """
    logger.info("Updating all videos with placeholder subtitles")
    
    # Get videos with placeholder subtitles
    with get_db_session() as session:
        # Find videos with placeholder subtitles using a join
        query = text("""
        SELECT v.id FROM videos v
        JOIN subtitles s ON v.id = s.video_id
        WHERE s.text LIKE 'Subtitles would be downloaded here for%'
        GROUP BY v.id
        """)
        
        video_ids = [row[0] for row in session.execute(query)]
        
        if max_videos:
            video_ids = video_ids[:max_videos]
        
        logger.info(f"Found {len(video_ids)} videos with placeholder subtitles")
    
    # Update each video
    for i, video_id in enumerate(video_ids):
        try:
            logger.info(f"Updating video {i+1}/{len(video_ids)}: {video_id}")
            update_video_subtitles(video_id)
        except Exception as e:
            logger.error(f"Failed to update subtitles for video {video_id}: {e}", exc_info=True)

def ingest_channel(channel_id: str = YOUTUBE_CHANNEL_ID, max_videos: int = None) -> None:
    """
    Ingest all videos from a channel.
    
    Args:
        channel_id: YouTube channel ID
        max_videos: Maximum number of videos to ingest (None for all)
    """
    logger.info(f"Ingesting videos from channel {channel_id}")
    
    # Get videos from channel
    videos = []
    next_page_token = None
    
    while True:
        video_batch, next_page_token = get_channel_videos(
            channel_id=channel_id,
            page_token=next_page_token
        )
        
        videos.extend(video_batch)
        
        if not next_page_token or (max_videos and len(videos) >= max_videos):
            break
    
    # Limit number of videos if specified
    if max_videos:
        videos = videos[:max_videos]
    
    logger.info(f"Found {len(videos)} videos in channel {channel_id}")
    
    # Extract video IDs
    video_ids = []
    for video in videos:
        video_id = video["contentDetails"]["videoId"]
        video_ids.append(video_id)
    
    # Ingest each video
    for video_id in video_ids:
        try:
            ingest_video(video_id)
        except Exception as e:
            logger.error(f"Failed to ingest video {video_id}: {e}", exc_info=True)

def ingest_document(url: str, doc_type: str, title: str, related_video_id: Optional[str] = None) -> None:
    """
    Ingest a document.
    
    Args:
        url: Document URL
        doc_type: Document type (pdf, sheet)
        title: Document title
        related_video_id: Related YouTube video ID (optional)
    """
    logger.info(f"Ingesting document {title} from {url}")
    
    # Store document metadata in database
    with get_db_session() as session:
        # Check if document already exists
        existing_doc = session.query(Document).filter(Document.source_url == url).first()
        if existing_doc:
            logger.info(f"Document {url} already exists, updating metadata")
            
            # Update metadata
            existing_doc.title = title
            existing_doc.doc_type = doc_type
            existing_doc.related_video_id = related_video_id
            
            document = existing_doc
        else:
            logger.info(f"Creating new document record for {url}")
            
            # Create new document
            document = Document(
                title=title,
                source_url=url,
                doc_type=doc_type,
                related_video_id=related_video_id
            )
            session.add(document)
            session.flush()  # Flush to get the ID
    
    # Process document
    doc_chunks = process_document(url, doc_type)
    
    # Process document content into chunks
    chunks = process_document_content(doc_chunks)
    
    # Add document_id to chunks
    for chunk in chunks:
        chunk["document_id"] = document.id
    
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
        session.query(TextChunk).filter(TextChunk.document_id == document.id).delete()
        
        # Add new chunks
        for chunk in chunks_with_embeddings:
            text_chunk = TextChunk(
                text=chunk["text"],
                document_id=chunk["document_id"],
                chunk_index=chunk["chunk_index"],
                vector_id=chunk["vector_id"]
            )
            session.add(text_chunk)
    
    logger.info(f"Successfully ingested document {title}")

def main():
    """Main entry point for the ingest script."""
    parser = argparse.ArgumentParser(description="Ingest data from YouTube or documents")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Video command
    video_parser = subparsers.add_parser("video", help="Ingest a single video")
    video_parser.add_argument("video_id", help="YouTube video ID")
    video_parser.add_argument("--force", action="store_true", help="Force transcription even if subtitles exist")
    
    # Channel command
    channel_parser = subparsers.add_parser("channel", help="Ingest all videos from a channel")
    channel_parser.add_argument("--channel_id", default=YOUTUBE_CHANNEL_ID, help="YouTube channel ID")
    channel_parser.add_argument("--max", type=int, help="Maximum number of videos to ingest")
    
    # Document command
    doc_parser = subparsers.add_parser("document", help="Ingest a document")
    doc_parser.add_argument("url", help="Document URL")
    doc_parser.add_argument("type", choices=["pdf", "sheet"], help="Document type")
    doc_parser.add_argument("title", help="Document title")
    doc_parser.add_argument("--related-video", help="Related YouTube video ID")
    
    # Update subtitles command
    update_parser = subparsers.add_parser("update-subtitles", help="Update placeholder subtitles")
    update_parser.add_argument("--video-id", help="YouTube video ID (if not provided, update all)")
    update_parser.add_argument("--max", type=int, help="Maximum number of videos to update")
    
    args = parser.parse_args()
    
    if args.command == "video":
        ingest_video(args.video_id, args.force)
    elif args.command == "channel":
        ingest_channel(args.channel_id, args.max)
    elif args.command == "document":
        ingest_document(args.url, args.type, args.title, args.related_video)
    elif args.command == "update-subtitles":
        if args.video_id:
            update_video_subtitles(args.video_id)
        else:
            update_all_placeholder_subtitles(args.max)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 