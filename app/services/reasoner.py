from __future__ import annotations

import json
import re
from typing import Any

from app.config import Settings

try:
    from google import genai
except ImportError:  # pragma: no cover
    genai = None


class ReasonerService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        if settings.gemini_api_key and genai is not None:
            self._client = genai.Client(api_key=settings.gemini_api_key)

    def _keyword_set(self, text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower())
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "into",
            "their",
            "journal",
            "focus",
            "scope",
        }
        return {w for w in words if w not in stop_words}

    def _fallback_reasons(self, title: str, abstract: str, journal: dict) -> list[str]:
        query_keywords = self._keyword_set(f"{title} {abstract}")
        journal_keywords = self._keyword_set(journal.get("full_text", ""))
        overlap = sorted(query_keywords & journal_keywords)

        if overlap:
            top_overlap = ", ".join(overlap[:4])
            return [
                f"Kecocokan kata kunci utama ditemukan pada area: {top_overlap}.",
                "Fokus jurnal memiliki irisan topik yang kuat dengan konteks riset pada abstrak.",
                "Ruang lingkup jurnal mendukung pendekatan metodologis dan domain penelitian yang diajukan.",
            ]

        return [
            "Kecocokan dipilih berdasarkan kemiripan semantik tertinggi antara abstrak dan cakupan jurnal.",
            "Fokus jurnal masih relevan dengan tema penelitian walau overlap kata kunci eksplisit terbatas.",
            "Jurnal ini mencakup area lintas disiplin yang mendukung topik penelitian Anda.",
        ]

    def _extract_text(self, response: Any) -> str:
        if response is None:
            return ""
        if hasattr(response, "text") and response.text:
            return str(response.text)
        if isinstance(response, dict):
            text = response.get("text")
            if isinstance(text, str):
                return text
        return ""

    def _generate_with_gemini(self, title: str, abstract: str, candidates: list[dict]) -> dict[str, list[str]]:
        if self._client is None:
            return {}

        compact_candidates = [
            {
                "journal_id": item["id"],
                "journal_name": item["name"],
                "focus": item.get("focus", "")[:600],
                "scope": item.get("scope", "")[:800],
            }
            for item in candidates
        ]

        prompt = (
            "Anda adalah asisten rekomendasi jurnal. "
            "Berikan alasan yang faktual dan singkat berdasarkan data kandidat. "
            "Keluarkan JSON valid saja dengan format: "
            "{\"items\":[{\"journal_id\":\"...\",\"reasons\":[\"...\",\"...\",\"...\"]}]}.\n\n"
            f"Judul: {title}\n"
            f"Abstrak: {abstract}\n"
            f"Kandidat: {json.dumps(compact_candidates, ensure_ascii=False)}"
        )

        response = self._client.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt,
        )
        text = self._extract_text(response)
        if not text:
            return {}

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}

        payload = json.loads(match.group(0))
        result: dict[str, list[str]] = {}
        for item in payload.get("items", []):
            jid = item.get("journal_id")
            reasons = item.get("reasons") or []
            if jid and isinstance(reasons, list):
                result[jid] = [str(r) for r in reasons[:4]]
        return result

    def generate_reasons(self, title: str, abstract: str, candidates: list[dict]) -> dict[str, list[str]]:
        try:
            from_model = self._generate_with_gemini(title=title, abstract=abstract, candidates=candidates)
            if from_model:
                return from_model
        except Exception:
            pass

        fallback: dict[str, list[str]] = {}
        for journal in candidates:
            fallback[journal["id"]] = self._fallback_reasons(title=title, abstract=abstract, journal=journal)
        return fallback
