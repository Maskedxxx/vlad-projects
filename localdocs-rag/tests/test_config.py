"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from localdocs_rag.config import LocalDocsConfig, load_config


class TestLocalDocsConfig:
    """Test LocalDocsConfig model."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LocalDocsConfig(openai_api_key="test-key")
        
        assert config.chunk_size == 500
        assert config.chunk_overlap == 50
        assert config.top_k == 3
        assert config.max_tokens == 1000
        assert config.model_name == "gpt-3.5-turbo"
        assert config.temperature == 0.1
        assert config.embedding_model == "text-embedding-3-small"
    
    def test_validation_chunk_size(self):
        """Test chunk size validation."""
        # Valid chunk size
        config = LocalDocsConfig(openai_api_key="test-key", chunk_size=1000)
        assert config.chunk_size == 1000
        
        # Invalid chunk size (too small)
        with pytest.raises(ValidationError):
            LocalDocsConfig(openai_api_key="test-key", chunk_size=50)
        
        # Invalid chunk size (too large)
        with pytest.raises(ValidationError):
            LocalDocsConfig(openai_api_key="test-key", chunk_size=3000)
    
    def test_validation_top_k(self):
        """Test top_k validation."""
        # Valid top_k
        config = LocalDocsConfig(openai_api_key="test-key", top_k=5)
        assert config.top_k == 5
        
        # Invalid top_k (too small)
        with pytest.raises(ValidationError):
            LocalDocsConfig(openai_api_key="test-key", top_k=0)
        
        # Invalid top_k (too large)
        with pytest.raises(ValidationError):
            LocalDocsConfig(openai_api_key="test-key", top_k=15)
    
    def test_path_resolution(self):
        """Test path resolution."""
        config = LocalDocsConfig(
            openai_api_key="test-key",
            data_dir="./test_data",
            index_dir="./test_index"
        )
        
        # Paths should be resolved to absolute paths
        assert config.data_dir.is_absolute()
        assert config.index_dir.is_absolute()
    
    def test_ensure_directories(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / "data"
            index_dir = tmp_path / "index"
            
            config = LocalDocsConfig(
                openai_api_key="test-key",
                data_dir=data_dir,
                index_dir=index_dir
            )
            
            # Directories should not exist yet
            assert not data_dir.exists()
            assert not index_dir.exists()
            
            # Create directories
            config.ensure_directories()
            
            # Directories should now exist
            assert data_dir.exists()
            assert index_dir.exists()


class TestLoadConfig:
    """Test config loading function."""
    
    def test_load_config_with_env_vars(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
        monkeypatch.setenv("LOCALDOCS_CHUNK_SIZE", "800")
        monkeypatch.setenv("LOCALDOCS_TOP_K", "5")
        
        config = load_config()
        
        assert config.openai_api_key == "test-api-key"
        assert config.chunk_size == 800
        assert config.top_k == 5
    
    def test_load_config_missing_api_key(self, monkeypatch):
        """Test loading config without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        with pytest.raises(ValidationError):
            load_config()
    
    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up test environment."""
        # Ensure clean environment for each test
        for key in os.environ:
            if key.startswith("LOCALDOCS_") or key == "OPENAI_API_KEY":
                monkeypatch.delenv(key, raising=False)