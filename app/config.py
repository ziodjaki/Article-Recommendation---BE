from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_bool(value: str, default: bool = False) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_origins(value: str) -> tuple[str, ...]:
    # CORS origin matching is exact; remove trailing slash to match Origin header.
    return tuple(origin.rstrip("/") for origin in _parse_csv(value))


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    gemini_embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
    top_k: int = int(os.getenv("TOP_K", "3"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.35"))
    journal_source_path: str = os.getenv("JOURNAL_SOURCE_PATH", "../jurnal.md")
    allowed_origins: tuple[str, ...] = _parse_origins(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000"))
    allowed_hosts: tuple[str, ...] = _parse_csv(os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"))
    enforce_api_key: bool = _parse_bool(os.getenv("ENFORCE_API_KEY", "false"), default=False)
    api_keys: tuple[str, ...] = _parse_csv(os.getenv("API_KEYS", ""))
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    max_request_size_bytes: int = int(os.getenv("MAX_REQUEST_SIZE_BYTES", "120000"))
    trust_proxy_headers: bool = _parse_bool(os.getenv("TRUST_PROXY_HEADERS", "false"), default=False)

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def data_dir(self) -> Path:
        return self.backend_root / "app" / "data"

    @property
    def journals_json_path(self) -> Path:
        return self.data_dir / "journals.json"

    @property
    def embeddings_json_path(self) -> Path:
        return self.data_dir / "embeddings.json"

    @property
    def journal_markdown_path(self) -> Path:
        candidate = Path(self.journal_source_path)
        if candidate.is_absolute():
            return candidate
        return (self.backend_root / candidate).resolve()


settings = Settings()
