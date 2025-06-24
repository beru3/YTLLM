from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Video(Base):
    """YouTube video metadata."""
    __tablename__ = "videos"
    
    id = Column(String(20), primary_key=True)  # YouTube video ID
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    thumbnail_url = Column(String(255), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    channel_id = Column(String(50), nullable=False)
    
    # Relationships
    subtitles = relationship("Subtitle", back_populates="video", cascade="all, delete-orphan")
    chunks = relationship("TextChunk", back_populates="video", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Video(id='{self.id}', title='{self.title}')>"


class Subtitle(Base):
    """Video subtitle/transcript data."""
    __tablename__ = "subtitles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(20), ForeignKey("videos.id"), nullable=False)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)    # End time in seconds
    text = Column(Text, nullable=False)
    is_auto_generated = Column(Boolean, default=False)
    language = Column(String(10), default="ja")
    
    # Relationships
    video = relationship("Video", back_populates="subtitles")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Subtitle(video_id='{self.video_id}', start={self.start_time}, end={self.end_time})>"


class Document(Base):
    """External documents like PDFs or Google Sheets."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    source_url = Column(String(255), nullable=False)
    doc_type = Column(String(20), nullable=False)  # pdf, sheet, etc.
    related_video_id = Column(String(20), ForeignKey("videos.id"), nullable=True)
    
    # Relationships
    chunks = relationship("TextChunk", back_populates="document", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', type='{self.doc_type}')>"


class TextChunk(Base):
    """Chunked text from videos or documents for vector storage."""
    __tablename__ = "text_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    video_id = Column(String(20), ForeignKey("videos.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    chunk_index = Column(Integer, nullable=False)  # Position in sequence
    
    # For video chunks
    start_time = Column(Float, nullable=True)  # Start time in seconds
    end_time = Column(Float, nullable=True)    # End time in seconds
    
    # Vector ID in ChromaDB
    vector_id = Column(String(64), nullable=True, unique=True)
    
    # Relationships
    video = relationship("Video", back_populates="chunks")
    document = relationship("Document", back_populates="chunks")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        source = f"video:{self.video_id}" if self.video_id else f"doc:{self.document_id}"
        return f"<TextChunk(id={self.id}, source={source}, index={self.chunk_index})>"


class QueryLog(Base):
    """Log of user queries and system responses."""
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=True)  # Anonymous if null
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    
    # References to sources used
    sources = Column(Text, nullable=True)  # JSON list of video_ids and document_ids
    
    # Performance metrics
    retrieval_time_ms = Column(Integer, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    total_time_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<QueryLog(id={self.id}, query='{self.query_text[:30]}...', time={self.total_time_ms}ms)>" 