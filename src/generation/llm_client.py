import logging
import json
from typing import List, Dict, Any, Optional
import requests

from config.config import DEEPSEEK_API_KEY, DEEPSEEK_CHAT_MODEL

logger = logging.getLogger(__name__)

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
        raise ValueError("DeepSeek API key is not set in environment variables")
    
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
        system_prompt = """You are a marketing expert assistant that provides accurate, helpful information based on the provided context. 
Follow these rules:
1. First try to answer based on the context provided.
2. If the context doesn't contain relevant information, provide a general answer based on your knowledge of marketing principles.
3. Always cite your sources by referencing the video or document IDs when using information from the context.
4. When providing general knowledge not in the context, indicate this clearly.
5. Keep responses concise and focused on marketing topics.
6. Format your response in a clear, structured way.
7. When mentioning specific techniques or strategies, explain how they can be applied."""
        
        # Create the user prompt
        user_prompt = f"Question: {query}\n\nPlease answer based on the following context:{context_text}"
        
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
        raise

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