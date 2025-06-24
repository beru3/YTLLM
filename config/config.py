import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# YouTube API configuration
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_EMBEDDING_MODEL = "deepseek-embedding"
DEEPSEEK_CHAT_MODEL = "deepseek-chat"
USE_DEEPSEEK = os.getenv("USE_DEEPSEEK", "True").lower() in ("true", "1", "t")

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
USE_OPENAI = os.getenv("USE_OPENAI", "False").lower() in ("true", "1", "t")

# Google Cloud credentials (for PDF/Sheets access)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Database configuration
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(PROCESSED_DATA_DIR / "chroma_db"))
SQLITE_PATH = os.getenv("SQLITE_PATH", str(PROCESSED_DATA_DIR / "app.db"))

# Whisper configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
CUDA_VISIBLE_DEVICES = os.getenv("CUDA_VISIBLE_DEVICES", "0")

# Text processing configuration
CHUNK_SIZE = 256  # tokens
CHUNK_OVERLAP = 50  # tokens

# Retrieval configuration
RETRIEVAL_TOP_K = 5  # Number of chunks to retrieve
HYBRID_ALPHA = 0.5  # Weight for hybrid search (0=BM25 only, 1=Vector only)

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "default_insecure_key")
SSO_CLIENT_ID = os.getenv("SSO_CLIENT_ID")
SSO_CLIENT_SECRET = os.getenv("SSO_CLIENT_SECRET")

# Batch job settings
BATCH_UPDATE_SCHEDULE = "0 0 * * *"  # Daily at midnight (cron format) 