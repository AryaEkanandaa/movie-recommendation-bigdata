from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PAYLOAD_PATH = (
    PROJECT_ROOT / "ml" / "data" / "processed" / "final" / "movies_payload.csv"
)


class Settings:
    def __init__(self) -> None:
        self.qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", "movies")
        self.qdrant_timeout_seconds = int(os.getenv("QDRANT_TIMEOUT_SECONDS", "30"))
        self.recommendation_candidate_k = int(
            os.getenv("RECOMMENDATION_CANDIDATE_K", "50")
        )
        self.payload_path = Path(
            os.getenv("MOVIES_PAYLOAD_PATH", str(DEFAULT_PAYLOAD_PATH))
        )
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv(
                "API_CORS_ORIGINS", "http://localhost:8501,http://localhost:3000"
            ).split(",")
            if origin.strip()
        ]
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        self.openai_timeout_seconds = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"
