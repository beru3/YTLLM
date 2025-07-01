#!/usr/bin/env python3
import sqlite3
import logging
import os
import sys
import time

# プロジェクトルートをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.ingest import ingest_video

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_placeholder_videos():
    """プレースホルダーテキストを含む動画IDを取得"""
    conn = sqlite3.connect('data/processed/app.db')
    cursor = conn.cursor()
    
    # プレースホルダーテキストを含む一意の動画IDを取得
    cursor.execute('''
        SELECT DISTINCT video_id 
        FROM text_chunks 
        WHERE text LIKE "Subtitles would be downloaded here%"
    ''')
    
    video_ids = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return video_ids

def delete_placeholder_chunks(video_id):
    """指定した動画IDのプレースホルダーチャンクを削除"""
    conn = sqlite3.connect('data/processed/app.db')
    cursor = conn.cursor()
    
    # 該当動画IDのプレースホルダーチャンクを削除
    cursor.execute('''
        DELETE FROM text_chunks 
        WHERE video_id = ? AND text LIKE "Subtitles would be downloaded here%"
    ''', (video_id,))
    
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return deleted_count

def main():
    """メイン処理"""
    logger.info("プレースホルダーテキストを含む動画を検索中...")
    video_ids = get_placeholder_videos()
    
    logger.info(f"プレースホルダーテキストを含む動画: {len(video_ids)}件")
    
    for i, video_id in enumerate(video_ids, 1):
        logger.info(f"処理中 ({i}/{len(video_ids)}): {video_id}")
        
        # プレースホルダーチャンクを削除
        deleted = delete_placeholder_chunks(video_id)
        logger.info(f"  削除したプレースホルダーチャンク: {deleted}件")
        
        # 動画を再取得
        try:
            ingest_video(video_id)
            logger.info(f"  動画 {video_id} の再取得に成功")
        except Exception as e:
            logger.error(f"  動画 {video_id} の再取得に失敗: {str(e)}")
        
        # APIレート制限を避けるために少し待機
        time.sleep(1)
    
    logger.info("すべての処理が完了しました")

if __name__ == "__main__":
    main() 