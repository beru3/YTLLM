# Marketing LLM System

A Retrieval-Augmented Generation (RAG) based LLM service specialized in marketing knowledge, leveraging content from the "Marketing Samurai" YouTube channel.

## Overview

This system processes marketing-related YouTube videos and associated documents to build a natural language searchable knowledge database. It uses DeepSeek's LLM and embedding APIs to provide high-quality marketing insights and recommendations.

## Key Features

- Extraction of YouTube video metadata and subtitles
- Transcription and response generation using DeepSeek API
- Document crawling for PDFs and Google Spreadsheets
- Vector-based semantic search using ChromaDB
- RAG response generation powered by DeepSeek Chat API
- Source attribution with links to original content
- Automatic daily batch updates for new content

## Project Structure

```
├── data/                  # Storage for raw and processed data
├── src/                   # Source code
│   ├── ingestion/         # Data ingestion components
│   ├── processing/        # Text processing and embeddings
│   ├── retrieval/         # Vector search and retrieval
│   ├── generation/        # LLM response generation
│   ├── api/               # FastAPI endpoints
│   └── utils/             # Helper functions
├── tests/                 # Test suite
├── config/                # Configuration files
└── notebooks/             # Development notebooks
```

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables in `.env` file (see `.env.example`)
4. Initialize the database: `python init_db.py`

## Usage

### 1. Starting the API Server

```
python run_api.py
```

The server will start at http://0.0.0.0:8000. To run in the background:

```
python run_api.py &
```

### 2. Making Queries

```
python test_query.py "your question"
```

Examples:
```
python test_query.py "What is marketing?"
python test_query.py "What are the 4Ps of marketing?"
```

### 3. Batch Updates (Fetching New Videos)

```
python -m src.ingestion.batch_update
```

This command fetches the latest video content and updates the database.

### 4. Environment Configuration

Settings are managed in the `.env` file. Main configuration items:
- `YOUTUBE_API_KEY`: YouTube API key
- `YOUTUBE_CHANNEL_ID`: UCW3MY7gdx-Gmha9IIx-EGfg (Marketing Samurai)
- `DEEPSEEK_API_KEY`: DeepSeek API key
- `USE_DEEPSEEK`: true (Whether to use DeepSeek API)

## Development Status

Current version: v0.1 (Draft)
Phase: Implementation complete

## License

For internal use only. All content from the "Marketing Samurai" YouTube channel is used under license agreement. 