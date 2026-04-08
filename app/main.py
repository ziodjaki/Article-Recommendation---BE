from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import RecommendRequest, RecommendResponse
from app.security import SecurityMiddleware, require_api_key
from app.services.embedding import EmbeddingService
from app.services.parser import parse_file_to_json
from app.services.reasoner import ReasonerService
from app.services.recommender import RecommenderService

journals_data: list[dict] = []
recommender_service: RecommenderService | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global journals_data, recommender_service

    journals_data = parse_file_to_json(
        source_path=settings.journal_markdown_path,
        output_path=settings.journals_json_path,
    )

    embedding_service = EmbeddingService(settings=settings)
    embedding_service.ensure_journal_embeddings(
        journals=journals_data,
        cache_path=settings.embeddings_json_path,
    )

    reasoner_service = ReasonerService(settings=settings)
    recommender_service = RecommenderService(
        settings=settings,
        embedding_service=embedding_service,
        reasoner_service=reasoner_service,
    )
    yield


app = FastAPI(title="Journal Recommender API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=list(settings.allowed_hosts) if settings.allowed_hosts else ["localhost", "127.0.0.1"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

app.add_middleware(
    SecurityMiddleware,
    rate_limit_requests=settings.rate_limit_requests,
    rate_limit_window_seconds=settings.rate_limit_window_seconds,
    max_request_size_bytes=settings.max_request_size_bytes,
    trust_proxy_headers=settings.trust_proxy_headers,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, RuntimeError):
        return JSONResponse(status_code=503, content={"detail": "Service unavailable"})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "journal-recommender-api"}


@app.post("/recommend", response_model=RecommendResponse)
def recommend(payload: RecommendRequest, _: None = Depends(require_api_key)) -> RecommendResponse:
    if recommender_service is None:
        raise RuntimeError("Service is not initialized")

    recommendations = recommender_service.recommend(
        title=payload.title,
        abstract=payload.abstract,
        journals=journals_data,
    )

    # Ensure plain JSON-serializable values.
    normalized = json.loads(json.dumps(recommendations))
    return RecommendResponse(recommendations=normalized)
