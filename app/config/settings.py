"""
Configuration settings for OllaPDF application.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    """Application configuration."""

    # Ollama settings
    ollama_host: str
    ollama_model_name: str

    # Directory settings
    data_dir: str

    # RAG settings
    default_temperature: float
    default_chunk_size: int
    default_chunk_overlap: int
    default_top_k: int

    # Embeddings settings
    embedding_model: str

    # Queue settings
    max_concurrent_requests: int

    # LLM settings
    llm_timeout: int


def load_config() -> AppConfig:
    """
    Load configuration from environment variables.

    Returns:
        AppConfig instance with loaded settings
    """
    return AppConfig(
        # Ollama settings
        ollama_host=os.getenv("OLLAMA_HOST", "http://ollama:11434"),
        ollama_model_name=os.getenv("OLLAMA_MODEL_NAME", "llama2"),

        # Directory settings
        data_dir=os.getenv("DATA_DIR", "data"),

        # RAG settings
        default_temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.1")),
        default_chunk_size=int(os.getenv("DEFAULT_CHUNK_SIZE", "1000")),
        default_chunk_overlap=int(os.getenv("DEFAULT_CHUNK_OVERLAP", "200")),
        default_top_k=int(os.getenv("DEFAULT_TOP_K", "4")),

        # Embeddings settings
        embedding_model=os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2"
        ),

        # Queue settings
        max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "1")),

        # LLM settings
        llm_timeout=int(os.getenv("LLM_TIMEOUT", "300")),
    )


# Global config instance
config = load_config()
