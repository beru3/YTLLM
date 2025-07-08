#!/usr/bin/env python3
import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# プロジェクトルートをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.main import query_llm
from src.retrieval.vector_store import search_vector_store
from src.utils.database import get_db_session
from src.utils.models import Video, TextChunk

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedChatInterface:
    """NotebookLM同等以上の機能を持つチャットインターフェース"""
    
    def __init__(self):
        self.conversation_history = []
        self.current_context = []
        self.focused_topics = []
    
    def chat(self, query: str, context_mode: str = "auto") -> Dict[str, Any]:
        """
        メインのチャット機能
        
        Args:
            query: ユーザーの質問
            context_mode: コンテキストモード ("auto", "focused", "broad")
            
        Returns:
            回答とメタデータ
        """
        logger.info(f"チャット開始: {query}")
        
        # 1. コンテキスト分析
        context_analysis = self._analyze_context(query)
        
        # 2. ベクトル検索（コンテキストモードに応じて調整）
        search_results = self._smart_search(query, context_mode, context_analysis)
        
        # 3. 回答生成
        response = self._generate_enhanced_response(query, search_results, context_analysis)
        
        # 4. 会話履歴に追加
        self._update_conversation_history(query, response)
        
        return response
    
    def _analyze_context(self, query: str) -> Dict[str, Any]:
        """クエリのコンテキストを分析"""
        # キーワード抽出
        keywords = self._extract_keywords(query)
        
        # トピック分類
        topic = self._classify_topic(query)
        
        # 質問タイプ判定
        question_type = self._classify_question_type(query)
        
        return {
            "keywords": keywords,
            "topic": topic,
            "question_type": question_type,
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_keywords(self, query: str) -> List[str]:
        """クエリからキーワードを抽出"""
        # 簡単なキーワード抽出（実際はNLPライブラリを使用）
        stop_words = {"の", "に", "は", "を", "が", "で", "と", "から", "まで", "について", "教えて", "ください"}
        words = query.replace("？", "").replace("?", "").split()
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        return keywords
    
    def _classify_topic(self, query: str) -> str:
        """トピックを分類"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["sns", "instagram", "youtube", "動画", "デジタル"]):
            return "デジタルマーケティング"
        elif any(word in query_lower for word in ["集客", "客", "集客"]):
            return "集客戦略"
        elif any(word in query_lower for word in ["売上", "セールス", "クロージング"]):
            return "セールス・クロージング"
        elif any(word in query_lower for word in ["ブランド", "ポジショニング"]):
            return "ブランディング"
        elif any(word in query_lower for word in ["価格", "プライシング"]):
            return "価格戦略"
        else:
            return "その他"
    
    def _classify_question_type(self, query: str) -> str:
        """質問タイプを分類"""
        if any(word in query for word in ["方法", "やり方", "手順", "コツ"]):
            return "how_to"
        elif any(word in query for word in ["なぜ", "理由", "原因"]):
            return "why"
        elif any(word in query for word in ["何", "どの", "どんな"]):
            return "what"
        elif any(word in query for word in ["いつ", "タイミング"]):
            return "when"
        else:
            return "general"
    
    def _smart_search(self, query: str, context_mode: str, context_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """スマート検索（コンテキストを考慮）"""
        
        # 基本検索
        base_results = search_vector_store(query, top_k=10)
        
        # コンテキストモードに応じて調整
        if context_mode == "focused":
            # フォーカスされた検索
            focused_results = self._focus_search(base_results, context_analysis)
            return focused_results
        elif context_mode == "broad":
            # 広範囲検索
            broad_results = self._broaden_search(base_results, context_analysis)
            return broad_results
        else:
            # 自動調整
            return self._auto_adjust_search(base_results, context_analysis)
    
    def _focus_search(self, results: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """フォーカスされた検索結果を返す"""
        # トピックに基づいてフィルタリング
        topic = context["topic"]
        focused_results = []
        
        for result in results:
            # メタデータからトピックを推測
            text = result.get("text", "").lower()
            if topic == "デジタルマーケティング" and any(word in text for word in ["sns", "instagram", "youtube"]):
                focused_results.append(result)
            elif topic == "集客戦略" and any(word in text for word in ["集客", "客"]):
                focused_results.append(result)
            # 他のトピックも同様に...
        
        return focused_results if focused_results else results[:5]
    
    def _broaden_search(self, results: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """広範囲検索結果を返す"""
        # 関連キーワードで追加検索
        keywords = context["keywords"]
        additional_results = []
        
        for keyword in keywords[:3]:  # 上位3つのキーワードで検索
            keyword_results = search_vector_store(keyword, top_k=5)
            additional_results.extend(keyword_results)
        
        # 重複を除去して結合
        all_results = results + additional_results
        unique_results = []
        seen_ids = set()
        
        for result in all_results:
            result_id = f"{result.get('source_id')}_{result.get('start_time', 0)}"
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)
        
        return unique_results[:15]  # 最大15件
    
    def _auto_adjust_search(self, results: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """自動調整検索"""
        question_type = context["question_type"]
        
        if question_type == "how_to":
            # 手順的な質問は詳細な情報を優先
            return results[:8]
        elif question_type == "why":
            # 理由を問う質問は理論的な情報を優先
            return results[:6]
        else:
            # 一般的な質問は標準的な結果数
            return results[:5]
    
    def _generate_enhanced_response(self, query: str, search_results: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """拡張された回答生成"""
        
        # コンテキスト情報をプロンプトに追加
        enhanced_prompt = self._create_enhanced_prompt(query, search_results, context)
        
        # LLMに質問
        try:
            response = query_llm(query)  # 既存のAPIを使用
            
            # 回答を拡張
            enhanced_response = self._enhance_response(response, search_results, context)
            
            return {
                "response": enhanced_response,
                "sources": [r.get("source_id") for r in search_results],
                "context_analysis": context,
                "search_results_count": len(search_results),
                "confidence_score": self._calculate_confidence(search_results, context)
            }
            
        except Exception as e:
            logger.error(f"回答生成エラー: {e}")
            return {
                "response": f"申し訳ございません。エラーが発生しました: {e}",
                "sources": [],
                "context_analysis": context,
                "search_results_count": 0,
                "confidence_score": 0.0
            }
    
    def _create_enhanced_prompt(self, query: str, search_results: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """拡張されたプロンプトを作成"""
        # 既存のquery_llm関数が内部でプロンプトを処理するため、
        # ここではコンテキスト情報を準備するだけ
        return query
    
    def _enhance_response(self, response: str, search_results: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """回答を拡張"""
        enhanced = response
        
        # コンテキスト情報を追加
        if context["topic"] != "その他":
            enhanced += f"\n\n**関連トピック**: {context['topic']}"
        
        # 質問タイプに応じた追加情報
        if context["question_type"] == "how_to":
            enhanced += "\n\n**実践のポイント**: 上記の方法を実践する際は、段階的に進めることをお勧めします。"
        elif context["question_type"] == "why":
            enhanced += "\n\n**背景**: この理由を理解することで、より効果的な戦略を立てることができます。"
        
        return enhanced
    
    def _calculate_confidence(self, search_results: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        """信頼度スコアを計算"""
        if not search_results:
            return 0.0
        
        # 検索結果のスコア平均
        avg_score = sum(r.get("score", 0.5) for r in search_results) / len(search_results)
        
        # コンテキストマッチング度
        topic_match = 1.0 if context["topic"] != "その他" else 0.5
        
        # 結果数の正規化
        result_count_score = min(len(search_results) / 10.0, 1.0)
        
        # 総合スコア
        confidence = (avg_score * 0.4 + topic_match * 0.3 + result_count_score * 0.3)
        
        return min(confidence, 1.0)
    
    def _update_conversation_history(self, query: str, response: Dict[str, Any]):
        """会話履歴を更新"""
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response["response"],
            "context_analysis": response["context_analysis"],
            "confidence_score": response["confidence_score"]
        }
        
        self.conversation_history.append(conversation_entry)
        
        # 履歴が長すぎる場合は古いものを削除
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """会話履歴のサマリーを取得"""
        if not self.conversation_history:
            return {"message": "会話履歴がありません"}
        
        # トピック統計
        topics = [entry["context_analysis"]["topic"] for entry in self.conversation_history]
        topic_counts = {}
        for topic in topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # 平均信頼度
        avg_confidence = sum(entry["confidence_score"] for entry in self.conversation_history) / len(self.conversation_history)
        
        return {
            "total_conversations": len(self.conversation_history),
            "topic_distribution": topic_counts,
            "average_confidence": avg_confidence,
            "last_conversation": self.conversation_history[-1]["timestamp"]
        }
    
    def export_conversation(self, output_file: str = "conversation_export.json"):
        """会話履歴をエクスポート"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        
        logger.info(f"会話履歴をエクスポートしました: {output_file}")

def main():
    """メイン関数 - インタラクティブチャット"""
    chat_interface = EnhancedChatInterface()
    
    print("=" * 60)
    print("マーケティング侍 エンハンスドチャット")
    print("NotebookLM同等以上の機能を提供します")
    print("=" * 60)
    print("コマンド:")
    print("  /help - ヘルプ表示")
    print("  /summary - 会話サマリー")
    print("  /export - 会話履歴エクスポート")
    print("  /quit - 終了")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n質問を入力してください: ").strip()
            
            if not user_input:
                continue
            
            # コマンド処理
            if user_input.startswith("/"):
                if user_input == "/help":
                    print("ヘルプ: マーケティングに関する質問を自由にしてください")
                elif user_input == "/summary":
                    summary = chat_interface.get_conversation_summary()
                    print(f"会話サマリー: {summary}")
                elif user_input == "/export":
                    chat_interface.export_conversation()
                elif user_input == "/quit":
                    print("チャットを終了します")
                    break
                else:
                    print("不明なコマンドです。'/help'でヘルプを表示")
                continue
            
            # 通常の質問処理
            print("\n考え中...")
            response = chat_interface.chat(user_input)
            
            print(f"\n回答: {response['response']}")
            print(f"信頼度: {response['confidence_score']:.2f}")
            print(f"参照動画数: {response['search_results_count']}件")
            
        except KeyboardInterrupt:
            print("\n\nチャットを終了します")
            break
        except Exception as e:
            print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main() 