"""Configuration management for LocalDocs RAG CLI."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class LocalDocsConfig(BaseSettings):
    """Configuration for LocalDocs RAG CLI."""
    
    # API Keys
    openai_api_key: str = Field(..., description="OpenAI API key")
    
    # Paths
    data_dir: Path = Field(default=Path("./data"), description="Directory containing documents")
    index_dir: Path = Field(default=Path("./.localdocs"), description="Directory for storing index files")
    
    # Text Processing
    chunk_size: int = Field(default=500, ge=100, le=2000, description="Size of text chunks")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="Overlap between chunks")
    
    # Retrieval
    top_k: int = Field(default=3, ge=1, le=10, description="Number of documents to retrieve")
    
    # Generation
    max_tokens: int = Field(default=1000, ge=100, le=4000, description="Maximum tokens for LLM response")
    model_name: str = Field(default="gpt-5-mini-2025-08-07", description="OpenAI model name")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="Temperature for LLM generation")
    
    # Embeddings
    embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")
    
    class Config:
        env_prefix = "LOCALDOCS_"
        env_file = ".env"
        case_sensitive = False
        
    @validator("data_dir", "index_dir")
    def resolve_paths(cls, v: Path) -> Path:
        """Resolve relative paths to absolute paths."""
        return v.expanduser().resolve()
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)


class DocumentMetadata(BaseModel):
    """Metadata for processed documents."""
    
    source: str = Field(..., description="Source file path")
    page: Optional[int] = Field(None, description="Page number (for PDFs)")
    chunk_id: int = Field(..., description="Chunk identifier")
    total_chunks: int = Field(..., description="Total number of chunks in document")
    file_type: str = Field(..., description="File type (pdf, docx, md)")
    created_at: str = Field(..., description="Processing timestamp")


class IndexMetadata(BaseModel):
    """Metadata for the vector index."""
    
    total_documents: int = Field(default=0, description="Total number of processed documents")
    total_chunks: int = Field(default=0, description="Total number of text chunks")
    embedding_model: str = Field(..., description="Embedding model used")
    index_version: str = Field(default="1.0", description="Index format version")
    created_at: str = Field(..., description="Index creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


def load_config() -> LocalDocsConfig:
    """Load configuration from environment variables and .env file."""
    return LocalDocsConfig()