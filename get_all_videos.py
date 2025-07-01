#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import json
from typing import List, Dict, Any, Optional, Tuple

# プロジェクトルートをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.youtube import get_channel_videos
from config.config import YOUTUBE_CHANNEL_ID

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_all_channel_videos(channel_id: str, output_file: str) -> None:
    """
    チャンネルの全動画を取得してファイルに保存する
    
    Args:
        channel_id: YouTubeチャンネルID
        output_file: 出力ファイルパス
    """
    logger.info(f"チャンネル {channel_id} の全動画を取得中...")
    
    all_videos = []
    next_page_token = None
    page_count = 0
    
    # ページネーションを使用して全動画を取得
    while True:
        page_count += 1
        logger.info(f"ページ {page_count} を取得中...")
        
        videos, next_page_token = get_channel_videos(
            channel_id=channel_id,
            max_results=50,  # YouTube APIの最大値
            page_token=next_page_token
        )
        
        if not videos:
            logger.warning(f"ページ {page_count} で動画が見つかりませんでした")
            break
        
        # 動画IDを抽出
        for video in videos:
            video_id = video["contentDetails"]["videoId"]
            video_title = video["snippet"]["title"]
            published_at = video["snippet"]["publishedAt"]
            
            all_videos.append({
                "id": video_id,
                "title": video_title,
                "published_at": published_at
            })
        
        logger.info(f"現在の動画数: {len(all_videos)}")
        
        # 次のページがなければ終了
        if not next_page_token:
            break
    
    # 結果をファイルに保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_videos, f, ensure_ascii=False, indent=2)
    
    logger.info(f"合計 {len(all_videos)} 件の動画情報を {output_file} に保存しました")

def main():
    parser = argparse.ArgumentParser(description='YouTubeチャンネルの全動画を取得')
    parser.add_argument('--channel', default=YOUTUBE_CHANNEL_ID,
                        help='YouTubeチャンネルID')
    parser.add_argument('--output', default='all_videos.json',
                        help='出力ファイルパス')
    
    args = parser.parse_args()
    
    get_all_channel_videos(args.channel, args.output)

if __name__ == "__main__":
    main() 