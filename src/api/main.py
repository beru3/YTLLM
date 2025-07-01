import time
import logging
from typing import List, Dict, Any, Optional
import json
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.retrieval.vector_store import search_vector_store
from src.generation.llm_client import generate_response, format_response_with_sources
from src.utils.database import get_db_session
from src.utils.models import QueryLog

from config.config import API_HOST, API_PORT, DEBUG

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Marketing LLM API",
    description="API for marketing knowledge retrieval and generation",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request/response models
class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    retrieval_time_ms: int
    generation_time_ms: int
    total_time_ms: int

@app.on_event("startup")
async def startup_event():
    """ログ出力を追加して、APIサーバーが起動したことを明確に表示します。"""
    logger.info("="*50)
    logger.info(f"Marketing LLM API サーバーが起動しました！")
    logger.info(f"サーバーURL: http://{API_HOST}:{API_PORT}")
    logger.info(f"API ドキュメント: http://{API_HOST}:{API_PORT}/docs")
    logger.info(f"デバッグモード: {DEBUG}")
    logger.info("="*50)

@app.get("/")
async def root():
    """Root endpoint for health check."""
    logger.info("ルートエンドポイントにアクセスがありました")
    return {"status": "ok", "message": "Marketing LLM API is running"}

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Process a natural language query and return a response.
    """
    logger.info(f"クエリを受信しました: {request.query}")
    start_time = time.time()
    
    try:
        # Step 1: Retrieve relevant chunks
        retrieval_start = time.time()
        chunks = search_vector_store(request.query, top_k=request.top_k)
        retrieval_time = time.time() - retrieval_start
        logger.info(f"検索完了: {len(chunks)}件のチャンクを取得 ({int(retrieval_time * 1000)}ms)")
        
        # Step 2: Generate response
        generation_start = time.time()
        response = generate_response(request.query, chunks)
        generation_time = time.time() - generation_start
        logger.info(f"レスポンス生成完了 ({int(generation_time * 1000)}ms)")
        
        # Format response with sources
        formatted_response = format_response_with_sources(response)
        
        # Calculate timings
        total_time = time.time() - start_time
        
        # Log the query
        with get_db_session() as session:
            query_log = QueryLog(
                user_id=request.user_id,
                query_text=request.query,
                response_text=formatted_response,
                sources=json.dumps([c.get("source_id") for c in chunks]),
                retrieval_time_ms=int(retrieval_time * 1000),
                generation_time_ms=int(generation_time * 1000),
                total_time_ms=int(total_time * 1000)
            )
            session.add(query_log)
        
        logger.info(f"クエリ処理完了: 合計処理時間 {int(total_time * 1000)}ms")
        return QueryResponse(
            response=formatted_response,
            sources=response["sources"],
            retrieval_time_ms=int(retrieval_time * 1000),
            generation_time_ms=int(generation_time * 1000),
            total_time_ms=int(total_time * 1000)
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    logger.info("ヘルスチェックエンドポイントにアクセスがありました")
    return {
        "status": "healthy",
        "version": "0.1.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print(f"Marketing LLM API サーバーを起動しています...")
    print(f"サーバーURL: http://{API_HOST}:{API_PORT}")
    print(f"API ドキュメント: http://{API_HOST}:{API_PORT}/docs")
    print("="*50 + "\n")
    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=DEBUG) 