#!/usr/bin/env python3
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.main import query_llm
from src.retrieval.vector_store import search_vector_store

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# マーケティング関連の質問リスト
MARKETING_QUESTIONS = [
    # 集客・集客戦略
    "SNSで集客する最強の方法を教えてください",
    "予算をかけずに集客できる方法はありますか？",
    "アナログ集客の具体的な手法を教えてください",
    "リピーターを増やすための戦略は？",
    "見込み客を教育する方法を教えてください",
    
    # セールス・クロージング
    "売上を倍増させるセールステクニックは？",
    "お客様の購買意欲を高める方法を教えてください",
    "クロージング率を上げるコピーライティングのコツは？",
    "価格交渉で勝つ方法を教えてください",
    "お客様の不安を解消する方法は？",
    
    # ブランディング・ポジショニング
    "個人ブランドを構築する方法を教えてください",
    "競合との差別化戦略は？",
    "ブランド価値を高める方法を教えてください",
    "ターゲット層を明確にする方法は？",
    "コンセプトメイキングのコツを教えてください",
    
    # 価格戦略・プライシング
    "商品の適正価格を決める方法を教えてください",
    "高価格でも売れる価格設定のコツは？",
    "プレミアム価格で販売する戦略を教えてください",
    "値下げせずに売る方法は？",
    "プライシング戦略の種類と使い分けを教えてください",
    
    # デジタルマーケティング
    "Instagramで集客する方法を教えてください",
    "YouTubeチャンネルを成功させるコツは？",
    "バズるコンテンツの作り方を教えてください",
    "SNSでフォロワーを増やす方法は？",
    "動画コンテンツで集客する戦略を教えてください",
    
    # ウェブマーケティング
    "ランディングページで成約率を上げる方法は？",
    "ホームページから集客に繋げる方法を教えてください",
    "SEO対策の具体的な方法は？",
    "Google広告の効果的な運用方法を教えてください",
    "メールマガジンで売上を上げる方法は？",
    
    # ビジネス戦略・経営
    "新規事業を成功させる方法を教えてください",
    "事業をスケールアップする戦略は？",
    "競合分析の方法を教えてください",
    "市場参入のタイミングを見極める方法は？",
    "事業撤退の判断基準を教えてください",
    
    # 組織・人材
    "優秀な人材を採用する方法を教えてください",
    "チームビルディングのコツを教えてください",
    "社員のモチベーションを上げる方法は？",
    "リーダーシップを発揮する方法を教えてください",
    "外注化で効率化する方法は？",
    
    # 心理・行動経済学
    "お客様の購買心理を理解する方法を教えてください",
    "感情を動かすマーケティング手法は？",
    "顧客の行動を予測する方法を教えてください",
    "信頼関係を構築する方法は？",
    "顧客のニーズを掘り下げる方法を教えてください",
    
    # 実践的な質問
    "明日から実践できるマーケティング手法を教えてください",
    "予算100万円でできるマーケティング戦略は？",
    "時間がない経営者が効率的にマーケティングする方法は？",
    "初心者でもできるマーケティング手法を教えてください",
    "売上が伸びない原因と対策を教えてください"
]

def export_qa_pairs(output_dir: str = "notebooklm_qa", questions: list = None):
    """
    Q&AペアをNotebookLM用にエクスポート
    
    Args:
        output_dir: 出力ディレクトリ
        questions: 質問リスト（Noneの場合はデフォルトリストを使用）
    """
    if questions is None:
        questions = MARKETING_QUESTIONS
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    logger.info(f"Q&Aペアを {output_path} にエクスポート中...")
    
    # 全体のQ&Aファイル
    qa_file = output_path / "00_マーケティングQ&A.txt"
    
    with open(qa_file, 'w', encoding='utf-8') as f:
        f.write("マーケティング侍 YouTubeチャンネル Q&A集\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"質問数: {len(questions)} 件\n\n")
        
        for i, question in enumerate(questions, 1):
            logger.info(f"質問 {i}/{len(questions)}: {question}")
            
            try:
                # LLMに質問
                response = query_llm(question)
                
                f.write(f"【質問 {i}】\n")
                f.write(f"Q: {question}\n")
                f.write(f"A: {response}\n")
                f.write("-" * 60 + "\n\n")
                
                # API制限を避けるため少し待機
                import time
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"質問 {i} でエラー: {e}")
                f.write(f"【質問 {i}】\n")
                f.write(f"Q: {question}\n")
                f.write(f"A: [エラーが発生しました: {e}]\n")
                f.write("-" * 60 + "\n\n")
    
    logger.info(f"Q&Aエクスポート完了: {qa_file}")

def export_categorized_qa(output_dir: str = "notebooklm_qa"):
    """
    カテゴリ別にQ&Aをエクスポート
    
    Args:
        output_dir: 出力ディレクトリ
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # カテゴリ別の質問
    categories = {
        "集客戦略": [
            "SNSで集客する最強の方法を教えてください",
            "予算をかけずに集客できる方法はありますか？",
            "アナログ集客の具体的な手法を教えてください",
            "リピーターを増やすための戦略は？",
            "見込み客を教育する方法を教えてください"
        ],
        "セールス・クロージング": [
            "売上を倍増させるセールステクニックは？",
            "お客様の購買意欲を高める方法を教えてください",
            "クロージング率を上げるコピーライティングのコツは？",
            "価格交渉で勝つ方法を教えてください",
            "お客様の不安を解消する方法は？"
        ],
        "ブランディング": [
            "個人ブランドを構築する方法を教えてください",
            "競合との差別化戦略は？",
            "ブランド価値を高める方法を教えてください",
            "ターゲット層を明確にする方法は？",
            "コンセプトメイキングのコツを教えてください"
        ],
        "デジタルマーケティング": [
            "Instagramで集客する方法を教えてください",
            "YouTubeチャンネルを成功させるコツは？",
            "バズるコンテンツの作り方を教えてください",
            "SNSでフォロワーを増やす方法は？",
            "動画コンテンツで集客する戦略を教えてください"
        ],
        "実践的アドバイス": [
            "明日から実践できるマーケティング手法を教えてください",
            "予算100万円でできるマーケティング戦略は？",
            "時間がない経営者が効率的にマーケティングする方法は？",
            "初心者でもできるマーケティング手法を教えてください",
            "売上が伸びない原因と対策を教えてください"
        ]
    }
    
    for category, questions in categories.items():
        category_file = output_path / f"01_{category}_Q&A.txt"
        
        with open(category_file, 'w', encoding='utf-8') as f:
            f.write(f"{category} - Q&A集\n")
            f.write("=" * 30 + "\n\n")
            f.write(f"作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"質問数: {len(questions)} 件\n\n")
            
            for i, question in enumerate(questions, 1):
                logger.info(f"{category} - 質問 {i}/{len(questions)}: {question}")
                
                try:
                    # LLMに質問
                    response = query_llm(question)
                    
                    f.write(f"【質問 {i}】\n")
                    f.write(f"Q: {question}\n")
                    f.write(f"A: {response}\n")
                    f.write("-" * 40 + "\n\n")
                    
                    # API制限を避けるため少し待機
                    import time
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"{category} - 質問 {i} でエラー: {e}")
                    f.write(f"【質問 {i}】\n")
                    f.write(f"Q: {question}\n")
                    f.write(f"A: [エラーが発生しました: {e}]\n")
                    f.write("-" * 40 + "\n\n")
        
        logger.info(f"{category} Q&Aエクスポート完了: {category_file}")

def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Q&AペアをNotebookLM用にエクスポート')
    parser.add_argument('--output', default='notebooklm_qa',
                        help='出力ディレクトリ')
    parser.add_argument('--categorized', action='store_true',
                        help='カテゴリ別にエクスポート')
    parser.add_argument('--questions', nargs='+',
                        help='特定の質問リスト（例: "質問1" "質問2"）')
    
    args = parser.parse_args()
    
    if args.questions:
        # 特定の質問リストでエクスポート
        export_qa_pairs(args.output, args.questions)
    elif args.categorized:
        # カテゴリ別にエクスポート
        export_categorized_qa(args.output)
    else:
        # デフォルトの質問リストでエクスポート
        export_qa_pairs(args.output)
    
    print(f"\nQ&Aエクスポート完了！")
    print(f"出力先: {args.output}/")
    print(f"\nNotebookLMでの使用方法:")
    print(f"1. {args.output}/ フォルダ内のファイルをNotebookLMにアップロード")
    print(f"2. マーケティングに関する質問を開始")
    print(f"3. 例: '集客戦略について詳しく教えてください'")
    print(f"4. 例: 'SNSマーケティングの最新手法は？'")

if __name__ == "__main__":
    main() 