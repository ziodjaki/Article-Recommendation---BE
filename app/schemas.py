from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(..., min_length=10, max_length=300)
    abstract: str = Field(..., min_length=80, max_length=8000)

    @field_validator("title", "abstract")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        # Block hidden control characters frequently used in payload obfuscation.
        if re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", value):
            raise ValueError("Input contains invalid control characters")
        return value


class JournalRecommendation(BaseModel):
    journal_id: str
    journal_name: str
    score: float
    confidence: str
    reasons: list[str]


class RecommendResponse(BaseModel):
    recommendations: list[JournalRecommendation]
