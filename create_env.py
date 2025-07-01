#!/usr/bin/env python
import os
import shutil

def create_env_file():
    """Create a .env file from env.example with the correct YouTube channel ID."""
    env_content = """# YouTube API credentials
YOUTUBE_API_KEY=AIzaSyDPMp6GN-ZDHjIRgBp_IgzpTHmkFZnGQVI
YOUTUBE_CHANNEL_ID=UCW3MY7gdx-Gmha9IIx-EGfg

# DeepSeek API credentials
DEEPSEEK_API_KEY=your_deepseek_api_key_here
USE_DEEPSEEK=true

# OpenAI API credentials
OPENAI_API_KEY=your_openai_api_key_here
USE_OPENAI=false

# Google Cloud credentials (for PDF/Sheets access)
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json

# Database configuration
CHROMA_DB_PATH=data/processed/chroma_db
SQLITE_PATH=data/processed/app.db

# Whisper configuration
WHISPER_MODEL=large-v3
CUDA_VISIBLE_DEVICES=0

# API settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# Security
SECRET_KEY=your_secret_key_for_jwt
SSO_CLIENT_ID=google_workspace_client_id
SSO_CLIENT_SECRET=google_workspace_client_secret
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("Created .env file with the correct YouTube channel ID")

if __name__ == "__main__":
    create_env_file() 