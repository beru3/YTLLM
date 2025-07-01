#!/usr/bin/env python3
import os
import sys
import logging
import argparse
from datetime import datetime
from tabulate import tabulate
from colorama import Fore, Style, init

# プロジェクトルートをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.database import get_db_session
from src.utils.models import Video, Subtitle, TextChunk
from src.ingestion.youtube import get_channel_videos, format_video_data

# カラー表示の初期化
init()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_ingested_videos():
    """データベースに取り込まれている動画のリストを取得"""
    with get_db_session() as session:
        videos = session.query(Video).all()
        
        # 各動画について字幕とチャンクの数を取得
        result = []
        for video in videos:
            subtitle_count = session.query(Subtitle).filter(Subtitle.video_id == video.id).count()
            chunk_count = session.query(TextChunk).filter(TextChunk.video_id == video.id).count()
            
            # プレースホルダーテキストを含むチャンクがあるかチェック
            has_placeholder = session.query(TextChunk).filter(
                TextChunk.video_id == video.id,
                TextChunk.text.like("Subtitles would be downloaded here%")
            ).count() > 0
            
            result.append({
                'id': video.id,
                'title': video.title,
                'published_at': video.published_at,
                'subtitle_count': subtitle_count,
                'chunk_count': chunk_count,
                'has_placeholder': has_placeholder
            })
        
        return result

def get_channel_all_videos(channel_id):
    """チャンネルの全動画を取得"""
    try:
        videos = get_channel_videos(channel_id)
        return [format_video_data(v) for v in videos]
    except Exception as e:
        logger.error(f"チャンネル動画の取得中にエラーが発生しました: {str(e)}")
        return []

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='動画の取り込み状況を一覧表示')
    parser.add_argument('--channel', '-c', help='YouTubeチャンネルID')
    args = parser.parse_args()
    
    # データベースに取り込まれている動画を取得
    logger.info("データベースから取り込み済み動画を取得中...")
    ingested_videos = get_ingested_videos()
    ingested_ids = {v['id'] for v in ingested_videos}
    
    if args.channel:
        # チャンネルの全動画を取得
        logger.info(f"チャンネル {args.channel} の全動画を取得中...")
        all_videos = get_channel_all_videos(args.channel)
        all_ids = {v['id'] for v in all_videos}
        
        # 未取り込みの動画を特定
        not_ingested_ids = all_ids - ingested_ids
        not_ingested_videos = [v for v in all_videos if v['id'] in not_ingested_ids]
        
        # チャンネルIDが指定されていれば、未取り込み動画も表示
        print(f"\n{Fore.CYAN}===== 未取り込み動画 ({len(not_ingested_videos)}件) ====={Style.RESET_ALL}")
        if not_ingested_videos:
            table_data = []
            for video in not_ingested_videos:
                published_at = video.get('published_at', datetime.now()).strftime('%Y-%m-%d')
                table_data.append([
                    video['id'],
                    video.get('title', '不明なタイトル')[:50] + ('...' if len(video.get('title', '')) > 50 else ''),
                    published_at
                ])
            
            print(tabulate(
                table_data,
                headers=['動画ID', 'タイトル', '公開日'],
                tablefmt='pretty'
            ))
        else:
            print("未取り込みの動画はありません。")
    
    # 取り込み済み動画の表示
    print(f"\n{Fore.GREEN}===== 取り込み済み動画 ({len(ingested_videos)}件) ====={Style.RESET_ALL}")
    if ingested_videos:
        # 字幕プレースホルダーがある動画を特定
        placeholder_videos = [v for v in ingested_videos if v['has_placeholder']]
        normal_videos = [v for v in ingested_videos if not v['has_placeholder']]
        
        # 通常の取り込み済み動画
        if normal_videos:
            print(f"\n{Fore.GREEN}--- 正常に取り込まれた動画 ({len(normal_videos)}件) ---{Style.RESET_ALL}")
            table_data = []
            for video in normal_videos:
                published_at = video['published_at'].strftime('%Y-%m-%d')
                table_data.append([
                    video['id'],
                    video['title'][:50] + ('...' if len(video['title']) > 50 else ''),
                    published_at,
                    video['subtitle_count'],
                    video['chunk_count']
                ])
            
            print(tabulate(
                table_data,
                headers=['動画ID', 'タイトル', '公開日', '字幕数', 'チャンク数'],
                tablefmt='pretty'
            ))
        
        # プレースホルダーがある動画
        if placeholder_videos:
            print(f"\n{Fore.YELLOW}--- 字幕プレースホルダーがある動画 ({len(placeholder_videos)}件) ---{Style.RESET_ALL}")
            table_data = []
            for video in placeholder_videos:
                published_at = video['published_at'].strftime('%Y-%m-%d')
                table_data.append([
                    video['id'],
                    video['title'][:50] + ('...' if len(video['title']) > 50 else ''),
                    published_at,
                    video['subtitle_count'],
                    video['chunk_count']
                ])
            
            print(tabulate(
                table_data,
                headers=['動画ID', 'タイトル', '公開日', '字幕数', 'チャンク数'],
                tablefmt='pretty'
            ))
            
            print(f"\n{Fore.YELLOW}注意: プレースホルダーがある動画は 'fix_subtitles.py' で修正できます{Style.RESET_ALL}")
    else:
        print("取り込み済みの動画はありません。")

if __name__ == "__main__":
    main() 