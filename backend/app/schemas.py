from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MovieSummary(BaseModel):
    id: int
    title: str
    release_year: int | None = None
    genres: str | None = None
    original_language: str | None = None
    runtime: int | None = None
    director: str | None = None
    cast: str | None = None
    keywords: str | None = None
    vote_average: float | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None


class Recommendation(MovieSummary):
    similarity_score: float
    hybrid_score: float
    reason: str
    score_type: Literal["similarity", "discovery"] = "similarity"


class MovieIntent(BaseModel):
    reference_title: str | None = Field(
        default=None,
        description="Movie title explicitly mentioned by the user, otherwise null.",
    )
    preferred_genres: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    original_languages: list[str] = Field(default_factory=list)
    min_rating: float | None = None
    max_rating: float | None = None
    release_year_from: int | None = None
    release_year_to: int | None = None
    min_runtime: int | None = None
    max_runtime: int | None = None
    clarification_needed: bool = False
    clarification_question: str | None = None


class SearchMoviesResponse(BaseModel):
    query: str
    results: list[MovieSummary]


class SimilarMoviesResponse(BaseModel):
    source: MovieSummary
    recommendations: list[Recommendation]


class DiscoverMoviesResponse(BaseModel):
    filters: MovieIntent
    results: list[Recommendation]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=20)


class QueryAnalysis(BaseModel):
    original_query: str
    interpreter: Literal["openai", "fallback_pattern"]
    llm_model: str | None = None
    extracted_intent: MovieIntent
    execution_mode: Literal["similarity", "discovery", "clarification"]
    backend_query: str
    execution_parameters: dict[str, Any] = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    status: Literal[
        "recommendations", "needs_selection", "needs_clarification", "not_found"
    ]
    message: str
    source: MovieSummary | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    candidates: list[MovieSummary] = Field(default_factory=list)
    llm_used: bool = False
    llm_model: str | None = None
    query_analysis: QueryAnalysis | None = None
