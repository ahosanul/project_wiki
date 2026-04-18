"""Configuration for erp-wiki-mcp server."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Data directory for SQLite and artifacts
    data_dir: str = "~/.local/share/erp-wiki-mcp"

    # Max file size to parse (MB)
    max_file_size_mb: int = 5

    # Max parallel parse workers
    max_parse_workers: int = 8

    # Allowed base paths (colon-separated on Unix)
    allowed_paths: str = "/home:/projects:/workspace"

    # Log level
    log_level: str = "INFO"

    # Groovy executable path
    groovy_executable: str = "groovy"

    # Embedding backend: local | openai
    embedding_backend: str = "local"

    # OpenAI API key
    openai_api_key: str = ""

    # Max traversal depth for graph operations
    max_traversal_depth: int = 5

    @property
    def data_path(self) -> Path:
        """Get expanded data directory path."""
        return Path(self.data_dir).expanduser()

    @property
    def db_path(self) -> Path:
        """Get SQLite database path."""
        return self.data_path / "registry.db"

    def get_allowed_paths(self) -> list[Path]:
        """Get list of allowed base paths."""
        separator = ";" if os.name == "nt" else ":"
        return [Path(p).expanduser().resolve() for p in self.allowed_paths.split(separator)]


settings = Settings()
