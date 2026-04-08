from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.services.embedding import EmbeddingService, cosine_similarity
from app.services.reasoner import ReasonerService


@dataclass
class RecommenderService:
    settings: Settings
    embedding_service: EmbeddingService
    reasoner_service: ReasonerService

    def _confidence_label(self, score: float) -> str:
        if score >= 0.75:
            return "high"
        if score >= 0.55:
            return "medium"
        return "low"

    def recommend(self, title: str, abstract: str, journals: list[dict]) -> list[dict]:
        if not journals:
            return []

        embeddings_map = self.embedding_service.ensure_journal_embeddings(
            journals=journals,
            cache_path=self.settings.embeddings_json_path,
        )
        query_vectors = self.embedding_service.embed_texts([title, abstract])
        if len(query_vectors) != 2:
            return []

        title_vec, abstract_vec = query_vectors
        scored: list[dict] = []

        for journal in journals:
            vector = embeddings_map.get(journal["id"])
            if vector is None:
                continue

            score_title = cosine_similarity(title_vec, vector)
            score_abstract = cosine_similarity(abstract_vec, vector)
            final_score = (0.35 * score_title) + (0.65 * score_abstract)

            scored.append(
                {
                    "journal": journal,
                    "score": round(float(final_score), 4),
                    "confidence": self._confidence_label(final_score),
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)

        top_candidates = scored[: self.settings.top_k]
        if not top_candidates:
            return []

        reason_map = self.reasoner_service.generate_reasons(
            title=title,
            abstract=abstract,
            candidates=[item["journal"] for item in top_candidates],
        )

        recommendations: list[dict] = []
        for item in top_candidates:
            journal = item["journal"]
            recommendations.append(
                {
                    "journal_id": journal["id"],
                    "journal_name": journal["name"],
                    "score": item["score"],
                    "confidence": item["confidence"],
                    "reasons": reason_map.get(journal["id"], []),
                }
            )

        return recommendations
