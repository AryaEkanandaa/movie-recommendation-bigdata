from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from .config import Settings
from .qdrant_gateway import QdrantGateway
from .schemas import MovieIntent, MovieSummary, Recommendation, SimilarMoviesResponse


HYBRID_WEIGHTS = {
    "similarity_score": 0.70,
    "rating_norm": 0.10,
    "vote_count_norm": 0.08,
    "popularity_norm": 0.07,
    "quality_norm": 0.05,
}

PAYLOAD_COLUMNS = [
    "id",
    "title",
    "release_year",
    "genres_text",
    "original_language",
    "runtime",
    "director_clean",
    "top_cast_text",
    "keywords_text",
    "overview_clean",
    "tagline_clean",
    "vote_average",
    "vote_count",
    "popularity",
    "recommendation_quality_score",
    "poster_path",
    "backdrop_path",
]

LANGUAGE_ALIASES = {
    "arabic": "ar",
    "bahasa indonesia": "id",
    "bahasa inggris": "en",
    "bahasa jepang": "ja",
    "bahasa korea": "ko",
    "chinese": "zh",
    "english": "en",
    "french": "fr",
    "german": "de",
    "hindi": "hi",
    "indonesia": "id",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "korea": "ko",
    "korean": "ko",
    "mandarin": "zh",
    "spanish": "es",
}


class MovieNotFoundError(LookupError):
    pass


class AmbiguousTitleError(LookupError):
    def __init__(self, query: str, candidates: list[MovieSummary]) -> None:
        super().__init__(f"Judul '{query}' memiliki beberapa kandidat.")
        self.candidates = candidates


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_language(value: str) -> str:
    normalized = normalize_title(value)
    return LANGUAGE_ALIASES.get(normalized, normalized)


def intent_has_filters(intent: MovieIntent | None) -> bool:
    if not intent:
        return False
    has_text_filters = any(
        term.strip()
        for values in [
            intent.preferred_genres,
            intent.actors,
            intent.directors,
            intent.keywords,
            intent.original_languages,
        ]
        for term in values
    )
    return any(
        [
            has_text_filters,
            intent.min_rating is not None,
            intent.max_rating is not None,
            intent.release_year_from is not None,
            intent.release_year_to is not None,
            intent.min_runtime is not None,
            intent.max_runtime is not None,
        ]
    )


def contains_any(value: str | None, terms: list[str]) -> bool:
    cleaned_terms = [term.strip() for term in terms if term.strip()]
    if not cleaned_terms:
        return True
    normalized = normalize_title(value or "")
    return any(normalize_title(term) in normalized for term in cleaned_terms)


def value_or_none(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


class MovieRecommender:
    def __init__(self, settings: Settings, gateway: QdrantGateway) -> None:
        if not settings.payload_path.exists():
            raise FileNotFoundError(
                f"Movies payload tidak ditemukan: {settings.payload_path}. "
                "Jalankan finalize_datasets.py terlebih dahulu."
            )

        self.settings = settings
        self.gateway = gateway
        self.movies = pd.read_csv(settings.payload_path, usecols=PAYLOAD_COLUMNS)
        self.movies["id"] = pd.to_numeric(self.movies["id"], errors="coerce")
        self.movies = self.movies.dropna(subset=["id", "title"]).copy()
        self.movies["id"] = self.movies["id"].astype("int64")
        self.movies["title_normalized"] = self.movies["title"].map(normalize_title)

        for column in [
            "release_year",
            "runtime",
            "vote_average",
            "vote_count",
            "popularity",
            "recommendation_quality_score",
        ]:
            self.movies[column] = pd.to_numeric(self.movies[column], errors="coerce")

        for column in [
            "vote_average",
            "vote_count",
            "popularity",
            "recommendation_quality_score",
        ]:
            self.movies[column] = self.movies[column].fillna(0.0)

        self.normalization_stats = {
            "max_vote_average": max(float(self.movies["vote_average"].max()), 1.0),
            "max_vote_count": max(float(self.movies["vote_count"].max()), 1.0),
            "max_popularity": max(float(self.movies["popularity"].max()), 1.0),
            "max_quality": max(
                float(self.movies["recommendation_quality_score"].max()), 1.0
            ),
        }

    def to_movie_summary(self, row: pd.Series | dict[str, Any]) -> MovieSummary:
        get = row.get if isinstance(row, dict) else row.get
        release_year = value_or_none(get("release_year"))
        vote_average = value_or_none(get("vote_average"))
        runtime = value_or_none(get("runtime"))
        return MovieSummary(
            id=int(get("id")),
            title=str(get("title")),
            release_year=int(release_year) if release_year is not None else None,
            genres=value_or_none(get("genres_text")),
            original_language=value_or_none(get("original_language")),
            runtime=int(runtime) if runtime is not None else None,
            director=value_or_none(get("director_clean")),
            cast=value_or_none(get("top_cast_text")),
            keywords=value_or_none(get("keywords_text")),
            vote_average=float(vote_average) if vote_average is not None else None,
            overview=value_or_none(get("overview_clean")),
            poster_path=value_or_none(get("poster_path")),
            backdrop_path=value_or_none(get("backdrop_path")),
        )

    def search_titles(self, query: str, limit: int = 10) -> list[MovieSummary]:
        normalized = normalize_title(query)
        if not normalized:
            return []

        exact = self.movies[self.movies["title_normalized"] == normalized]
        starts_with = self.movies[
            self.movies["title_normalized"].str.startswith(normalized, na=False)
        ]
        contains = self.movies[
            self.movies["title_normalized"].str.contains(
                re.escape(normalized), na=False, regex=True
            )
        ]
        candidates = pd.concat([exact, starts_with, contains]).drop_duplicates("id")
        candidates = candidates.sort_values(
            ["vote_count", "vote_average", "title"], ascending=[False, False, True]
        ).head(limit)
        return [self.to_movie_summary(row) for _, row in candidates.iterrows()]

    def _resolve_source(self, query: str) -> pd.Series:
        normalized = normalize_title(query)
        exact = self.movies[self.movies["title_normalized"] == normalized]
        if len(exact) == 1:
            return exact.iloc[0]

        candidates = self.search_titles(query, limit=8)
        if not candidates:
            raise MovieNotFoundError(f"Film '{query}' tidak ditemukan.")
        if len(candidates) > 1:
            raise AmbiguousTitleError(query, candidates)

        source_id = candidates[0].id
        return self.movies[self.movies["id"] == source_id].iloc[0]

    def _hybrid_score(self, payload: dict[str, Any], similarity_score: float) -> float:
        rating = float(value_or_none(payload.get("vote_average")) or 0.0)
        vote_count = float(value_or_none(payload.get("vote_count")) or 0.0)
        popularity = float(value_or_none(payload.get("popularity")) or 0.0)
        quality = float(
            value_or_none(payload.get("recommendation_quality_score")) or 0.0
        )

        return (
            HYBRID_WEIGHTS["similarity_score"] * similarity_score
            + HYBRID_WEIGHTS["rating_norm"]
            * (rating / self.normalization_stats["max_vote_average"])
            + HYBRID_WEIGHTS["vote_count_norm"]
            * (vote_count / self.normalization_stats["max_vote_count"])
            + HYBRID_WEIGHTS["popularity_norm"]
            * (popularity / self.normalization_stats["max_popularity"])
            + HYBRID_WEIGHTS["quality_norm"]
            * (quality / self.normalization_stats["max_quality"])
        )

    def recommend(self, title: str, top_k: int) -> SimilarMoviesResponse:
        source = self._resolve_source(title)
        source_id = int(source["id"])
        source_vector = self.gateway.get_vector(source_id)
        candidate_limit = max(self.settings.recommendation_candidate_k, top_k + 1)
        results = self.gateway.search(source_vector, candidate_limit)

        recommendations: list[Recommendation] = []
        for result in results:
            if int(result["id"]) == source_id:
                continue
            payload = result.get("payload") or {}
            similarity_score = float(result.get("score") or 0.0)
            hybrid_score = self._hybrid_score(payload, similarity_score)
            summary = self.to_movie_summary({"id": result["id"], **payload})
            recommendations.append(
                Recommendation(
                    **summary.model_dump(),
                    similarity_score=round(similarity_score, 4),
                    hybrid_score=round(hybrid_score, 4),
                    reason="Mirip berdasarkan metadata film dan diperkuat oleh kualitas/rating.",
                )
            )

        recommendations.sort(
            key=lambda item: (item.hybrid_score, item.similarity_score), reverse=True
        )
        return SimilarMoviesResponse(
            source=self.to_movie_summary(source), recommendations=recommendations[:top_k]
        )

    def _filter_movies(self, intent: MovieIntent) -> pd.DataFrame:
        filtered = self.movies

        text_filters = [
            ("genres_text", intent.preferred_genres),
            ("top_cast_text", intent.actors),
            ("director_clean", intent.directors),
        ]
        for column, terms in text_filters:
            cleaned_terms = [term.strip() for term in terms if term.strip()]
            if cleaned_terms:
                mask = pd.Series(False, index=filtered.index)
                for term in cleaned_terms:
                    mask |= filtered[column].fillna("").str.contains(
                        re.escape(term), case=False, regex=True
                    )
                filtered = filtered[mask]

        cleaned_keywords = [term.strip() for term in intent.keywords if term.strip()]
        if cleaned_keywords:
            mask = pd.Series(False, index=filtered.index)
            for term in cleaned_keywords:
                escaped = re.escape(term)
                for column in ["keywords_text", "overview_clean", "tagline_clean"]:
                    mask |= filtered[column].fillna("").str.contains(
                        escaped, case=False, regex=True
                    )
            filtered = filtered[mask]

        if intent.original_languages:
            languages = {
                normalize_language(item)
                for item in intent.original_languages
                if item.strip()
            }
            filtered = filtered[
                filtered["original_language"].fillna("").str.lower().isin(languages)
            ]
        if intent.min_rating is not None:
            filtered = filtered[filtered["vote_average"] >= intent.min_rating]
        if intent.max_rating is not None:
            filtered = filtered[filtered["vote_average"] <= intent.max_rating]
        if intent.release_year_from is not None:
            filtered = filtered[filtered["release_year"] >= intent.release_year_from]
        if intent.release_year_to is not None:
            filtered = filtered[filtered["release_year"] <= intent.release_year_to]
        if intent.min_runtime is not None:
            filtered = filtered[filtered["runtime"] >= intent.min_runtime]
        if intent.max_runtime is not None:
            filtered = filtered[filtered["runtime"] <= intent.max_runtime]
        return filtered

    def discover(self, intent: MovieIntent, limit: int) -> list[Recommendation]:
        if not intent_has_filters(intent):
            return []

        filtered = self._filter_movies(intent).copy()
        if filtered.empty:
            return []

        max_votes = math.log1p(self.normalization_stats["max_vote_count"])
        max_popularity = math.log1p(self.normalization_stats["max_popularity"])
        filtered["_discovery_score"] = (
            0.40 * (filtered["vote_average"] / self.normalization_stats["max_vote_average"])
            + 0.25 * (filtered["vote_count"].map(math.log1p) / max_votes)
            + 0.15 * (filtered["popularity"].map(math.log1p) / max_popularity)
            + 0.20
            * (
                filtered["recommendation_quality_score"]
                / self.normalization_stats["max_quality"]
            )
        ).clip(0.0, 1.0)
        filtered = filtered.sort_values(
            ["_discovery_score", "vote_count", "vote_average"],
            ascending=[False, False, False],
        ).head(limit)

        reason = build_filter_reason(intent)
        return [
            Recommendation(
                **self.to_movie_summary(row).model_dump(),
                similarity_score=0.0,
                hybrid_score=round(float(row["_discovery_score"]), 4),
                reason=reason,
                score_type="discovery",
            )
            for _, row in filtered.iterrows()
        ]


def extract_title_candidate(message: str) -> str:
    cleaned = re.sub(r"\s+", " ", message.strip())
    patterns = [r"(?:mirip|seperti|like)\s+(.+)$", r"(?:recommend|rekomendasi)\s+(.+)$"]
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .?!")
    return cleaned.strip(" .?!")


def apply_intent_filters(
    recommendations: list[Recommendation], intent: MovieIntent | None
) -> list[Recommendation]:
    if not intent:
        return recommendations

    filtered = recommendations
    if intent.preferred_genres:
        filtered = [
            movie
            for movie in filtered
            if contains_any(movie.genres, intent.preferred_genres)
        ]
    if intent.actors:
        filtered = [movie for movie in filtered if contains_any(movie.cast, intent.actors)]
    if intent.directors:
        filtered = [
            movie for movie in filtered if contains_any(movie.director, intent.directors)
        ]
    if intent.keywords:
        filtered = [
            movie
            for movie in filtered
            if contains_any(
                " ".join(
                    value
                    for value in [movie.keywords, movie.overview, movie.genres]
                    if value
                ),
                intent.keywords,
            )
        ]
    if intent.original_languages:
        languages = {
            normalize_language(item)
            for item in intent.original_languages
            if item.strip()
        }
        filtered = [
            movie
            for movie in filtered
            if normalize_language(movie.original_language or "") in languages
        ]
    if intent.min_rating is not None:
        filtered = [
            movie
            for movie in filtered
            if movie.vote_average is not None and movie.vote_average >= intent.min_rating
        ]
    if intent.max_rating is not None:
        filtered = [
            movie
            for movie in filtered
            if movie.vote_average is not None and movie.vote_average <= intent.max_rating
        ]
    if intent.release_year_from is not None:
        filtered = [
            movie
            for movie in filtered
            if movie.release_year is not None
            and movie.release_year >= intent.release_year_from
        ]
    if intent.release_year_to is not None:
        filtered = [
            movie
            for movie in filtered
            if movie.release_year is not None and movie.release_year <= intent.release_year_to
        ]
    if intent.min_runtime is not None:
        filtered = [
            movie
            for movie in filtered
            if movie.runtime is not None and movie.runtime >= intent.min_runtime
        ]
    if intent.max_runtime is not None:
        filtered = [
            movie
            for movie in filtered
            if movie.runtime is not None and movie.runtime <= intent.max_runtime
        ]
    return filtered


def build_filter_reason(intent: MovieIntent) -> str:
    parts: list[str] = []
    if intent.preferred_genres:
        parts.append(f"genre {', '.join(intent.preferred_genres)}")
    if intent.actors:
        parts.append(f"aktor {', '.join(intent.actors)}")
    if intent.directors:
        parts.append(f"sutradara {', '.join(intent.directors)}")
    if intent.keywords:
        parts.append(f"tema {', '.join(intent.keywords)}")
    if intent.original_languages:
        parts.append(f"bahasa {', '.join(intent.original_languages)}")
    if intent.min_rating is not None:
        parts.append(f"rating minimal {intent.min_rating:g}")
    if intent.max_rating is not None:
        parts.append(f"rating maksimal {intent.max_rating:g}")
    if intent.release_year_from is not None:
        parts.append(f"mulai tahun {intent.release_year_from}")
    if intent.release_year_to is not None:
        parts.append(f"sampai tahun {intent.release_year_to}")
    if intent.min_runtime is not None:
        parts.append(f"durasi minimal {intent.min_runtime} menit")
    if intent.max_runtime is not None:
        parts.append(f"durasi maksimal {intent.max_runtime} menit")
    return "Sesuai filter " + ", ".join(parts) + "."
