import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str
    max_upload_bytes: int
    retrieval_threshold: float
    retrieval_backend: str
    embedding_model: str
    model_provider: str
    model_name: str
    model_base_url: str
    model_api_key: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "ProofLens AI"),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))),
        retrieval_threshold=float(os.getenv("RETRIEVAL_THRESHOLD", "0.25")),
        retrieval_backend=os.getenv("RETRIEVAL_BACKEND", "lexical").lower(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        model_provider=os.getenv("MODEL_PROVIDER", "extractive"),
        model_name=os.getenv("MODEL_NAME", ""),
        model_base_url=os.getenv("MODEL_BASE_URL", ""),
        model_api_key=os.getenv("MODEL_API_KEY", ""),
    )