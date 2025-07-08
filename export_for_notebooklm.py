#!/usr/bin/env python3
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.database import get_db_session
from src.utils.models import Video, TextChunk
from src.retrieval.vector_store import search_vector_store

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def export_videos_to_text(output_dir: str = "notebooklm_export"):
    """
    ベクトルDBの動画情報をテキストファイルにエクスポート
    
    Args:
        output_dir: 出力ディレクトリ
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    logger.info(f"ベクトルDBの内容を {output_path} にエクスポート中...")
    
    with get_db_session() as session:
        # 動画情報を取得
        videos = session.query(Video).all()
        
        # 動画ごとのテキストチャンクを取得
        for video in videos:
            chunks = session.query(TextChunk).filter(TextChunk.video_id == video.id).all()
            
            if not chunks:
                continue
            
            # ファイル名を作成（特殊文字を除去）
            safe_title = "".join(c for c in video.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # 長すぎる場合は短縮
            filename = f"{video.id}_{safe_title}.txt"
            filepath = output_path / filename
            
            # テキストファイルに書き込み
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"動画タイトル: {video.title}\n")
                f.write(f"動画ID: {video.id}\n")
                f.write(f"URL: https://www.youtube.com/watch?v={video.id}\n")
                f.write(f"投稿日: {video.published_at}\n")
                f.write(f"視聴回数: {video.view_count}\n")
                f.write(f"チャンク数: {len(chunks)}\n")
                f.write("=" * 80 + "\n\n")
                
                # チャンクを時系列順に並べて書き込み
                sorted_chunks = sorted(chunks, key=lambda x: x.start_time or 0)
                
                for i, chunk in enumerate(sorted_chunks):
                    f.write(f"【チャンク {i+1}】\n")
                    if chunk.start_time is not None:
                        f.write(f"時間: {chunk.start_time:.1f}s - {chunk.end_time:.1f}s\n")
                    f.write(f"内容:\n{chunk.text}\n")
                    f.write("-" * 40 + "\n\n")
    
    logger.info(f"エクスポート完了: {len(videos)} 件の動画を {output_path} に保存")

def export_summary_for_notebooklm(output_dir: str = "notebooklm_export"):
    """
    NotebookLM用のサマリーファイルを作成
    
    Args:
        output_dir: 出力ディレクトリ
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    logger.info("NotebookLM用のサマリーファイルを作成中...")
    
    with get_db_session() as session:
        videos = session.query(Video).all()
        
        # 全体サマリーファイル
        summary_file = output_path / "00_全体サマリー.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("マーケティング侍 YouTubeチャンネル データベース\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"総動画数: {len(videos)} 件\n")
            f.write(f"エクスポート日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # カテゴリ別サマリー
            categories = {}
            for video in videos:
                # タイトルからカテゴリを推測
                title_lower = video.title.lower()
                if any(word in title_lower for word in ['sns', 'instagram', 'youtube', '動画']):
                    category = 'デジタルマーケティング'
                elif any(word in title_lower for word in ['集客', '集客', '客']):
                    category = '集客戦略'
                elif any(word in title_lower for word in ['売上', 'セールス', 'クロージング']):
                    category = 'セールス・クロージング'
                elif any(word in title_lower for word in ['ブランド', 'ポジショニング']):
                    category = 'ブランディング'
                elif any(word in title_lower for word in ['価格', 'プライシング']):
                    category = '価格戦略'
                else:
                    category = 'その他'
                
                if category not in categories:
                    categories[category] = []
                categories[category].append(video)
            
            f.write("カテゴリ別動画数:\n")
            for category, video_list in categories.items():
                f.write(f"- {category}: {len(video_list)} 件\n")
            
            f.write("\n" + "=" * 50 + "\n")
            f.write("NotebookLMでの使用方法:\n")
            f.write("1. このファイルをNotebookLMにアップロード\n")
            f.write("2. 特定のカテゴリについて質問\n")
            f.write("3. 例: '集客戦略について詳しく教えてください'\n")
            f.write("4. 例: 'SNSマーケティングの最新手法は？'\n")
    
    # カテゴリ別ファイル
    for category, video_list in categories.items():
        category_file = output_path / f"01_{category}.txt"
        with open(category_file, 'w', encoding='utf-8') as f:
            f.write(f"{category} - 動画リスト\n")
            f.write("=" * 30 + "\n\n")
            
            for video in video_list:
                # セッション内で属性にアクセス
                with get_db_session() as session:
                    video_refreshed = session.merge(video)
                    f.write(f"タイトル: {video_refreshed.title}\n")
                    f.write(f"URL: https://www.youtube.com/watch?v={video_refreshed.id}\n")
                    f.write(f"投稿日: {video_refreshed.published_at}\n")
                    f.write(f"視聴回数: {video_refreshed.view_count}\n\n")
    
    logger.info(f"サマリーファイル作成完了: {output_path}")

def export_search_results_for_notebooklm(query: str, output_dir: str = "notebooklm_export"):
    """
    特定のクエリで検索した結果をNotebookLM用にエクスポート
    
    Args:
        query: 検索クエリ
        output_dir: 出力ディレクトリ
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    logger.info(f"クエリ '{query}' の検索結果をエクスポート中...")
    
    # ベクトル検索を実行
    results = search_vector_store(query, top_k=10)
    
    # ファイル名を作成
    safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"検索結果_{safe_query[:30]}.txt"
    filepath = output_path / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"検索クエリ: {query}\n")
        f.write(f"検索日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"検索結果数: {len(results)} 件\n")
        f.write("=" * 60 + "\n\n")
        
        for i, result in enumerate(results):
            f.write(f"【結果 {i+1}】\n")
            f.write(f"スコア: {result.get('score', 'N/A'):.3f}\n")
            f.write(f"動画ID: {result.get('source_id', 'N/A')}\n")
            f.write(f"時間: {result.get('start_time', 'N/A')}s - {result.get('end_time', 'N/A')}s\n")
            f.write(f"URL: https://www.youtube.com/watch?v={result.get('source_id', '')}&t={int(result.get('start_time', 0))}\n")
            f.write(f"内容:\n{result.get('text', 'N/A')}\n")
            f.write("-" * 40 + "\n\n")
    
    logger.info(f"検索結果エクスポート完了: {filepath}")

def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ベクトルDBの内容をNotebookLM用にエクスポート')
    parser.add_argument('--output', default='notebooklm_export',
                        help='出力ディレクトリ')
    parser.add_argument('--query', 
                        help='特定のクエリで検索結果をエクスポート')
    parser.add_argument('--summary-only', action='store_true',
                        help='サマリーファイルのみ作成')
    
    args = parser.parse_args()
    
    if args.query:
        # 特定クエリの検索結果をエクスポート
        export_search_results_for_notebooklm(args.query, args.output)
    elif args.summary_only:
        # サマリーファイルのみ作成
        export_summary_for_notebooklm(args.output)
    else:
        # 全データをエクスポート
        export_videos_to_text(args.output)
        export_summary_for_notebooklm(args.output)
    
    print(f"\nエクスポート完了！")
    print(f"出力先: {args.output}/")
    print(f"\nNotebookLMでの使用方法:")
    print(f"1. {args.output}/ フォルダ内のファイルをNotebookLMにアップロード")
    print(f"2. マーケティングに関する質問を開始")
    print(f"3. 例: 'SNS集客の最新手法について教えてください'")

if __name__ == "__main__":
    main() 