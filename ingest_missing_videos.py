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

def get_missing_videos(input_file: str) -> list:
    """
    JSONファイルから、データベースに存在しない動画のみを抽出する
    
    Args:
        input_file: 入力ファイルパス（JSON形式）
        
    Returns:
        未取り込みの動画リスト
    """
    logger.info(f"ファイル {input_file} から未取り込み動画を抽出中...")
    
    # JSONファイルを読み込む
    with open(input_file, 'r', encoding='utf-8') as f:
        all_videos = json.load(f)
    
    logger.info(f"ファイルから {len(all_videos)} 件の動画情報を読み込みました")
    
    # 既存の動画IDを取得
    with get_db_session() as session:
        existing_videos = session.query(Video.id).all()
        existing_video_ids = {video.id for video in existing_videos}
    
    logger.info(f"データベース内の既存動画数: {len(existing_video_ids)} 件")
    
    # 未取り込みの動画を抽出
    missing_videos = []
    for video in all_videos:
        if video["id"] not in existing_video_ids:
            missing_videos.append(video)
    
    logger.info(f"未取り込み動画数: {len(missing_videos)} 件")
    
    return missing_videos

def ingest_missing_videos(missing_videos: list, start_index: int = 0, batch_size: int = None) -> None:
    """
    未取り込み動画を一つずつ取り込む
    
    Args:
        missing_videos: 未取り込み動画のリスト
        start_index: 開始インデックス（途中から再開する場合）
        batch_size: 処理する動画の数（Noneの場合は全て）
    """
    if not missing_videos:
        logger.info("未取り込み動画がありません")
        return
    
    # 開始インデックスと終了インデックスを設定
    if start_index >= len(missing_videos):
        logger.error(f"開始インデックス {start_index} が未取り込み動画数 {len(missing_videos)} を超えています")
        return
    
    end_index = len(missing_videos)
    if batch_size is not None:
        end_index = min(start_index + batch_size, len(missing_videos))
    
    target_videos = missing_videos[start_index:end_index]
    logger.info(f"処理対象の動画数: {len(target_videos)} 件（{start_index}～{end_index-1}）")
    
    # 動画を一つずつ取り込む
    success_count = 0
    error_count = 0
    
    for i, video in enumerate(tqdm(target_videos, desc="動画の取り込み")):
        video_id = video["id"]
        video_title = video["title"]
        
        try:
            logger.info(f"動画 {i+start_index}/{end_index-1}: {video_id} ({video_title}) を取り込み中...")
            ingest_video(video_id)
            success_count += 1
            
            # APIレート制限を避けるために少し待機
            time.sleep(1)
            
        except Exception as e:
            error_count += 1
            logger.error(f"動画 {video_id} の取り込みに失敗しました: {str(e)}")
    
    logger.info(f"処理が完了しました。成功: {success_count} 件, 失敗: {error_count} 件")
    
    # 残りの動画数を表示
    remaining = len(missing_videos) - end_index
    if remaining > 0:
        logger.info(f"残りの未取り込み動画数: {remaining} 件")
        logger.info(f"次回の実行コマンド: python {sys.argv[0]} --input all_videos.json --start {end_index}")

def main():
    parser = argparse.ArgumentParser(description='未取り込み動画のみを取り込む')
    parser.add_argument('--input', default='all_videos.json',
                        help='入力ファイルパス（JSON形式）')
    parser.add_argument('--start', type=int, default=0,
                        help='開始インデックス（未取り込み動画リスト内での位置）')
    parser.add_argument('--batch', type=int, default=None,
                        help='処理する動画の数')
    parser.add_argument('--list-only', action='store_true',
                        help='未取り込み動画のリストのみを表示（取り込みは行わない）')
    
    args = parser.parse_args()
    
    # 未取り込み動画を取得
    missing_videos = get_missing_videos(args.input)
    
    if args.list_only:
        logger.info("未取り込み動画のリスト:")
        for i, video in enumerate(missing_videos):
            logger.info(f"{i}: {video['id']} - {video['title']}")
        return
    
    # 未取り込み動画を取り込む
    ingest_missing_videos(missing_videos, args.start, args.batch)

if __name__ == "__main__":
    main() 