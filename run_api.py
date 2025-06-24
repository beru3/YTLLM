#!/usr/bin/env python
import uvicorn
from config.config import API_HOST, API_PORT, DEBUG

if __name__ == "__main__":
    print(f"Starting Marketing LLM API on {API_HOST}:{API_PORT}")
    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=DEBUG) 