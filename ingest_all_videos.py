#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import json
import time
from tqdm import tqdm

# プロジェクトルートをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.ingest import ingest_video
from src.utils.database import get_db_session
from src.utils.models import Video

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ingest_videos_from_file(input_file: str, start_index: int = 0, batch_size: int = None, force_update: bool = False) -> None:
    """
    JSONファイルから動画IDを読み込み、一つずつ取り込む
    
    Args:
        input_file: 入力ファイルパス（JSON形式）
        start_index: 開始インデックス（途中から再開する場合）
        batch_size: 処理する動画の数（Noneの場合は全て）
        force_update: 既存の動画も強制的に再取り込みするかどうか
    """
    logger.info(f"ファイル {input_file} から動画を取り込み中...")
    
    # JSONファイルを読み込む
    with open(input_file, 'r', encoding='utf-8') as f:
        all_videos = json.load(f)
    
    logger.info(f"ファイルから {len(all_videos)} 件の動画情報を読み込みました")
    
    # 開始インデックスと終了インデックスを設定
    if start_index >= len(all_videos):
        logger.error(f"開始インデックス {start_index} がファイル内の動画数 {len(all_videos)} を超えています")
        return
    
    end_index = len(all_videos)
    if batch_size is not None:
        end_index = min(start_index + batch_size, len(all_videos))
    
    target_videos = all_videos[start_index:end_index]
    logger.info(f"処理対象の動画数: {len(target_videos)} 件（{start_index}～{end_index-1}）")
    
    # 既存の動画IDを取得（force_update=Falseの場合にスキップするため）
    existing_video_ids = set()
    if not force_update:
        with get_db_session() as session:
            existing_videos = session.query(Video.id).all()
            existing_video_ids = {video.id for video in existing_videos}
        logger.info(f"データベース内の既存動画数: {len(existing_video_ids)} 件")
    
    # 動画を一つずつ取り込む
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, video in enumerate(tqdm(target_videos, desc="動画の取り込み")):
        video_id = video["id"]
        video_title = video["title"]
        
        # 既存の動画はスキップ（force_update=Falseの場合）
        if not force_update and video_id in existing_video_ids:
            logger.info(f"動画 {i+start_index}/{end_index-1}: {video_id} ({video_title}) は既に存在します。スキップします。")
            skip_count += 1
            continue
        
        try:
            logger.info(f"動画 {i+start_index}/{end_index-1}: {video_id} ({video_title}) を取り込み中...")
            ingest_video(video_id)
            success_count += 1
            
            # APIレート制限を避けるために少し待機
            time.sleep(1)
            
        except Exception as e:
            error_count += 1
            logger.error(f"動画 {video_id} の取り込みに失敗しました: {str(e)}")
    
    logger.info(f"処理が完了しました。成功: {success_count} 件, スキップ: {skip_count} 件, 失敗: {error_count} 件")
    
    # 残りの動画数を表示
    remaining = len(all_videos) - end_index
    if remaining > 0:
        logger.info(f"残りの動画数: {remaining} 件")
        logger.info(f"次回の実行コマンド: python {sys.argv[0]} --input {input_file} --start {end_index}")

def main():
    parser = argparse.ArgumentParser(description='JSONファイルから動画を取り込む')
    parser.add_argument('--input', default='all_videos.json',
                        help='入力ファイルパス（JSON形式）')
    parser.add_argument('--start', type=int, default=0,
                        help='開始インデックス（途中から再開する場合）')
    parser.add_argument('--batch', type=int, default=None,
                        help='処理する動画の数')
    parser.add_argument('--force', action='store_true',
                        help='既存の動画も強制的に再取り込みする')
    
    args = parser.parse_args()
    
    ingest_videos_from_file(args.input, args.start, args.batch, args.force)

if __name__ == "__main__":
    main() 