from dataclasses import dataclass
import errno
from pathlib import Path

from app.services.embedding import EmbeddingService
from app.services.parser import parse_file_to_json
from app.services.reasoner import ReasonerService
from app.services.recommender import RecommenderService


@dataclass
class RecommenderSettings:
    gemini_api_key: str
    gemini_model: str
    gemini_embedding_model: str
    top_k: int
    min_confidence: float
    embeddings_json_path: Path


def _load_journals(tmp_path: Path) -> tuple[list[dict], RecommenderSettings]:
    source = Path(__file__).resolve().parents[2] / "jurnal.md"
    journals_path = tmp_path / "journals.json"
    embeddings_path = tmp_path / "embeddings.json"

    journals = parse_file_to_json(source_path=source, output_path=journals_path)
    settings = RecommenderSettings(
        gemini_api_key="",
        gemini_model="gemini-2.5-pro",
        gemini_embedding_model="text-embedding-004",
        top_k=3,
        min_confidence=0.35,
        embeddings_json_path=embeddings_path,
    )

    return journals, settings


def test_embedding_cache_created(tmp_path: Path):
    journals, settings = _load_journals(tmp_path)
    embedding_service = EmbeddingService(settings=settings)

    result = embedding_service.ensure_journal_embeddings(journals=journals, cache_path=tmp_path / "embeddings.json")

    assert len(result) == len(journals)
    assert (tmp_path / "embeddings.json").exists()


def test_embedding_cache_read_only_filesystem_still_returns_vectors(monkeypatch, tmp_path: Path):
    journals, settings = _load_journals(tmp_path)
    embedding_service = EmbeddingService(settings=settings)

    def _raise_ero_fs(*args, **kwargs):
        raise OSError(errno.EROFS, "Read-only file system")

    monkeypatch.setattr(Path, "write_text", _raise_ero_fs)

    result = embedding_service.ensure_journal_embeddings(journals=journals, cache_path=tmp_path / "embeddings.json")

    assert len(result) == len(journals)


def test_ranking_sorted_descending(tmp_path: Path):
    journals, settings = _load_journals(tmp_path)
    embedding_service = EmbeddingService(settings=settings)
    reasoner_service = ReasonerService(settings=settings)
    recommender = RecommenderService(settings=settings, embedding_service=embedding_service, reasoner_service=reasoner_service)

    recommendations = recommender.recommend(
        title="AI based prediction for hybrid learning outcomes",
        abstract=(
            "This research proposes machine learning analytics for hybrid classrooms with predictive "
            "modelling, adaptive pedagogy, and learning performance monitoring across multicultural cohorts."
        ),
        journals=journals,
    )

    assert len(recommendations) <= 3
    scores = [item["score"] for item in recommendations]
    assert scores == sorted(scores, reverse=True)
