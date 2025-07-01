#!/usr/bin/env python
import os
import logging
import time
from datetime import datetime, timedelta
import json
import sys
from tqdm import tqdm
from colorama import Fore, Style, init

from src.ingestion.ingest import ingest_channel, update_video_subtitles
from src.utils.database import get_db_session
from src.utils.models import Video, TextChunk, Subtitle
from src.processing.text_processor import process_video_subtitles
from src.processing.embedding import generate_embeddings, store_embeddings
from src.retrieval.vector_store import add_chunks_to_vector_store

from config.config import YOUTUBE_CHANNEL_ID

# カラー表示の初期化
init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def print_status(message, status="INFO", end="\n"):
    """ステータスメッセージを色付きで表示する"""
    color = Fore.WHITE
    if status == "INFO":
        color = Fore.BLUE
    elif status == "SUCCESS":
        color = Fore.GREEN
    elif status == "WARNING":
        color = Fore.YELLOW
    elif status == "ERROR":
        color = Fore.RED
    elif status == "PROGRESS":
        color = Fore.CYAN
    
    print(f"{color}[{status}]{Style.RESET_ALL} {message}", end=end)
    sys.stdout.flush()

def batch_update():
    """
    Run a batch update to ingest new videos from the channel.
    """
    print_status("バッチ更新を開始します", "INFO")
    print_status("=" * 50, "INFO")
    
    # Get the latest video date from the database
    latest_video_date = None
    with get_db_session() as session:
        latest_video = session.query(Video).order_by(Video.published_at.desc()).first()
        if latest_video:
            latest_video_date = latest_video.published_at
    
    if latest_video_date:
        print_status(f"データベース内の最新動画日付: {latest_video_date}", "INFO")
    else:
        print_status("データベースに動画がありません。すべての動画を取得します。", "INFO")
    
    # Run the ingestion
    try:
        print_status(f"チャンネル {YOUTUBE_CHANNEL_ID} から動画を取得中...", "PROGRESS")
        start_time = time.time()
        
        # チャンネルから動画を取得
        ingest_channel(YOUTUBE_CHANNEL_ID)
        
        # 処理時間を計算
        elapsed_time = time.time() - start_time
        elapsed_str = str(timedelta(seconds=int(elapsed_time)))
        
        # 処理結果を表示
        print_status(f"バッチ更新が正常に完了しました（処理時間: {elapsed_str}）", "SUCCESS")
        
        # データベース内の動画数を取得
        with get_db_session() as session:
            video_count = session.query(Video).count()
            print_status(f"現在のデータベース内の動画数: {video_count}", "INFO")
    
    except Exception as e:
        print_status(f"バッチ更新に失敗しました: {e}", "ERROR")
        logger.error(f"Batch update failed: {e}", exc_info=True)
        return False
    
    # Record the update time
    with open("data/last_update.json", "w") as f:
        json.dump({
            "last_update": datetime.utcnow().isoformat(),
            "status": "success"
        }, f)
    
    print_status("=" * 50, "INFO")
    return True

def update_all_videos_with_accurate_timestamps(max_videos: int = None):
    """
    Update all existing videos with accurate timestamps for their text chunks.
    This function reprocesses the subtitles to create chunks with more accurate time ranges.
    
    Args:
        max_videos: Maximum number of videos to update (None for all)
    """
    print_status("すべての動画のタイムスタンプを更新します", "INFO")
    print_status("=" * 50, "INFO")
    
    # Get all videos with existing subtitles
    with get_db_session() as session:
        # Find videos with subtitles
        videos_with_subtitles = session.query(Video.id).join(Video.subtitles).group_by(Video.id).all()
        video_ids = [v[0] for v in videos_with_subtitles]
        
        if max_videos:
            video_ids = video_ids[:max_videos]
        
        total_videos = len(video_ids)
        print_status(f"タイムスタンプを更新する動画数: {total_videos}", "INFO")
    
    if not video_ids:
        print_status("更新する動画がありません", "WARNING")
        return True
    
    # 開始時間を記録
    start_time = time.time()
    
    # Update each video with progress bar
    success_count = 0
    error_count = 0
    
    for i, video_id in enumerate(tqdm(video_ids, desc="動画の処理", unit="videos")):
        try:
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
                print_status(f"動画 {video_id} に字幕がありません。スキップします。", "WARNING")
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
            
            success_count += 1
            
            # 残り時間の見積もり
            elapsed = time.time() - start_time
            videos_per_sec = (i + 1) / elapsed if elapsed > 0 else 0
            remaining_videos = total_videos - (i + 1)
            remaining_time = remaining_videos / videos_per_sec if videos_per_sec > 0 else 0
            remaining_str = str(timedelta(seconds=int(remaining_time)))
            
            # 進捗状況を更新（tqdmと競合しないよう、ログに出力）
            if (i + 1) % 5 == 0 or (i + 1) == total_videos:
                logger.info(f"進捗: {i+1}/{total_videos} 完了 - 残り推定時間: {remaining_str}")
            
            # Sleep to avoid overloading the system
            time.sleep(0.5)
            
        except Exception as e:
            error_count += 1
            print_status(f"動画 {video_id} のタイムスタンプ更新に失敗: {e}", "ERROR")
            logger.error(f"Failed to update timestamps for video {video_id}: {e}", exc_info=True)
    
    # 処理時間を計算
    elapsed_time = time.time() - start_time
    elapsed_str = str(timedelta(seconds=int(elapsed_time)))
    
    print_status(f"すべての動画のタイムスタンプ更新が完了しました", "SUCCESS")
    print_status(f"処理時間: {elapsed_str}", "INFO")
    print_status(f"成功: {success_count} 動画, 失敗: {error_count} 動画", "INFO")
    print_status("=" * 50, "INFO")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run batch update for video ingestion")
    parser.add_argument("--update-timestamps", action="store_true", help="Update all videos with accurate timestamps")
    parser.add_argument("--max", type=int, help="Maximum number of videos to process")
    
    args = parser.parse_args()
    
    print_status(f"\n{'='*20} 動画取り込み処理 {'='*20}", "INFO")
    print_status(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
    
    try:
        if args.update_timestamps:
            update_all_videos_with_accurate_timestamps(args.max)
        else:
            batch_update()
        print_status("処理が正常に完了しました", "SUCCESS")
    except KeyboardInterrupt:
        print_status("\n処理が中断されました", "WARNING")
    except Exception as e:
        print_status(f"処理中にエラーが発生しました: {e}", "ERROR")
    
    print_status(f"終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
    print_status(f"{'='*50}", "INFO") 