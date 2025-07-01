import logging
import json
from typing import List, Dict, Any, Optional
import requests

from config.config import DEEPSEEK_API_KEY, DEEPSEEK_CHAT_MODEL

logger = logging.getLogger(__name__)

def generate_dummy_response(query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a dummy response when API keys are not available.
    
    Args:
        query: User query
        context_chunks: List of relevant context chunks
        
    Returns:
        Response with generated text and source references
    """
    logger.warning("Using dummy response generator as API keys are not available")
    
    # Create a simple response that acknowledges the query and mentions the context
    response_text = f"ダミー回答: '{query}' についての質問をいただきました。\n\n"
    response_text += "現在、APIキーが設定されていないため、実際の回答は生成できません。\n"
    response_text += "有効なDeepSeekまたはOpenAIのAPIキーを設定してください。\n\n"
    
    # Add some information about the retrieved context
    if context_chunks:
        response_text += f"{len(context_chunks)}件の関連コンテキストが見つかりました。\n"
        for i, chunk in enumerate(context_chunks[:3]):  # Show only first 3 chunks
            source_type = chunk.get("source_type", "unknown")
            source_id = chunk.get("source_id", "unknown")
            response_text += f"- コンテキスト {i+1}: {source_type} {source_id} からの情報\n"
        
        if len(context_chunks) > 3:
            response_text += f"- その他 {len(context_chunks) - 3} 件のコンテキスト\n"
    else:
        response_text += "関連するコンテキストは見つかりませんでした。\n"
    
    # Extract source references
    sources = []
    for chunk in context_chunks:
        source = {
            "type": chunk.get("source_type"),
            "id": chunk.get("source_id")
        }
        
        if chunk.get("source_type") == "video":
            source["start_time"] = chunk.get("start_time", 0)
            source["end_time"] = chunk.get("end_time", 0)
            source["url"] = f"https://www.youtube.com/watch?v={chunk.get('source_id')}&t={int(chunk.get('start_time', 0))}"
        elif chunk.get("source_type") == "document":
            if "page" in chunk:
                source["page"] = chunk["page"]
            if "sheet_name" in chunk:
                source["sheet_name"] = chunk["sheet_name"]
        
        sources.append(source)
    
    return {
        "text": response_text,
        "sources": sources
    }

def generate_response(query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a response using DeepSeek Chat API.
    
    Args:
        query: User query
        context_chunks: List of relevant context chunks
        
    Returns:
        Response with generated text and source references
    """
    if not DEEPSEEK_API_KEY:
        logger.warning("DeepSeek API key is not set in environment variables")
        return generate_dummy_response(query, context_chunks)
    
    try:
        # Format context for the prompt
        context_text = ""
        for i, chunk in enumerate(context_chunks):
            # Add source information
            source_info = ""
            if chunk.get("source_type") == "video":
                video_id = chunk.get("source_id", "")
                start_time = chunk.get("start_time", 0)
                end_time = chunk.get("end_time", 0)
                source_info = f"[Video {video_id} at {start_time:.1f}s-{end_time:.1f}s]"
            elif chunk.get("source_type") == "document":
                doc_id = chunk.get("source_id", "")
                page = chunk.get("page", "")
                source_info = f"[Document {doc_id}" + (f", Page {page}]" if page else "]")
            
            # Add the chunk text with source info
            context_text += f"\n\n--- Context {i+1} {source_info} ---\n{chunk['text']}"
        
        # Create the system prompt
        system_prompt = """あなたはマーケティングの専門家アシスタントで、提供されたコンテキストに基づいて正確で役立つ情報を提供します。
以下のルールに従ってください：
1. まず、提供されたコンテキストに基づいて回答してください。
2. コンテキストに関連情報がない場合は、マーケティングの原則に基づいた一般的な回答を提供してください。
3. コンテキストから情報を使用する場合は、必ず動画やドキュメントIDを参照して出典を明記してください。
4. コンテキストにない一般的な知識を提供する場合は、それを明確に示してください。
5. 回答は簡潔にし、マーケティングのトピックに焦点を当ててください。
6. 回答は明確で構造化された形式で提供してください。
7. 特定の技術や戦略について言及する場合は、それらがどのように適用できるかを説明してください。
8. 必ず日本語で回答してください。"""
        
        # Create the user prompt
        user_prompt = f"質問: {query}\n\n以下のコンテキストに基づいて回答してください:{context_text}"
        
        # Call DeepSeek Chat API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": DEEPSEEK_CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,  # Lower temperature for more factual responses
            "max_tokens": 1000
        }
        
        # Make API request
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",  # Replace with actual endpoint
            headers=headers,
            json=payload
        )
        
        # Check for errors
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        generated_text = result["choices"][0]["message"]["content"]
        
        # Extract source references
        sources = []
        for chunk in context_chunks:
            source = {
                "type": chunk.get("source_type"),
                "id": chunk.get("source_id")
            }
            
            if chunk.get("source_type") == "video":
                source["start_time"] = chunk.get("start_time", 0)
                source["end_time"] = chunk.get("end_time", 0)
                source["url"] = f"https://www.youtube.com/watch?v={chunk.get('source_id')}&t={int(chunk.get('start_time', 0))}"
            elif chunk.get("source_type") == "document":
                if "page" in chunk:
                    source["page"] = chunk["page"]
                if "sheet_name" in chunk:
                    source["sheet_name"] = chunk["sheet_name"]
            
            sources.append(source)
        
        return {
            "text": generated_text,
            "sources": sources
        }
        
    except Exception as e:
        logger.error(f"Failed to generate response: {e}")
        # If API authentication fails or other errors occur, fall back to dummy response
        return generate_dummy_response(query, context_chunks)

def format_response_with_sources(response: Dict[str, Any]) -> str:
    """
    Format the response text with source references.
    
    Args:
        response: Response from generate_response()
        
    Returns:
        Formatted response text with source references
    """
    text = response["text"]
    sources = response["sources"]
    
    # Add source references at the end
    if sources:
        text += "\n\n**Sources:**"
        
        for i, source in enumerate(sources):
            if source["type"] == "video":
                video_id = source["id"]
                start_time = source.get("start_time", 0)
                end_time = source.get("end_time", 0)
                
                # Only include timestamp in URL if it's not 0
                url_timestamp = f"&t={int(start_time)}" if start_time > 0 else ""
                url = f"https://www.youtube.com/watch?v={video_id}{url_timestamp}"
                
                # Include time range in the citation if available and valid
                if start_time > 0 or end_time > 0:
                    text += f"\n{i+1}. [Video {video_id} at {int(start_time)}s]({url})"
                else:
                    text += f"\n{i+1}. [Video {video_id}]({url})"
            elif source["type"] == "document":
                doc_id = source["id"]
                page_info = f", Page {source['page']}" if "page" in source else ""
                sheet_info = f", Sheet: {source['sheet_name']}" if "sheet_name" in source else ""
                text += f"\n{i+1}. Document {doc_id}{page_info}{sheet_info}"
    
    return text 