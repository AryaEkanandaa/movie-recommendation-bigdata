"""
Evaluate Word2Vec + Qdrant recommendation examples.

Outputs:
- ml/reports/modelling/evaluation/recommendation_examples.csv
- ml/reports/modelling/evaluation/model_evaluation_summary.csv
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ML_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ML_DIR / "data" / "processed"
FINAL_DIR = PROCESSED_DIR / "final"
VECTOR_DIR = PROCESSED_DIR / "vectors"
REPORT_DIR = ML_DIR / "reports" / "modelling" / "evaluation"

VECTOR_PATH = VECTOR_DIR / "movie_vectors_word2vec.parquet"
PAYLOAD_PATH = FINAL_DIR / "movies_payload.csv"

RECOMMENDATION_EXAMPLES_OUTPUT = REPORT_DIR / "recommendation_examples.csv"
MODEL_EVALUATION_SUMMARY_OUTPUT = REPORT_DIR / "model_evaluation_summary.csv"

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "movies")
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

HYBRID_WEIGHTS = {
    "similarity_score": 0.70,
    "rating_norm": 0.10,
    "vote_count_norm": 0.08,
    "popularity_norm": 0.07,
    "quality_norm": 0.05,
}

TEST_QUERIES = [
    "Interstellar",
    "Inception",
    "The Dark Knight",
    "Titanic",
    "Toy Story",
    "Avatar",
    "Parasite",
    "La La Land",
    "Spirited Away",
]


def qdrant_request(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{QDRANT_URL}{path}"
    response = requests.request(method, url, timeout=120, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Qdrant request failed: {method} {url} "
            f"status={response.status_code} body={response.text[:500]}"
        )
    return response


def normalize_genres(genres: Any) -> set[str]:
    if pd.isna(genres):
        return set()
    return {part.strip().lower() for part in str(genres).split() if part.strip()}


def genre_overlap(source_genres: Any, recommended_genres: Any) -> float:
    source = normalize_genres(source_genres)
    recommended = normalize_genres(recommended_genres)
    if not source or not recommended:
        return 0.0
    return len(source & recommended) / len(source | recommended)


def find_movie_by_title(payload: pd.DataFrame, title: str) -> pd.Series:
    titles = payload["title"].fillna("")
    exact = payload[titles.str.lower() == title.lower()].sort_values(
        ["title", "release_year"]
    )
    fuzzy = payload[titles.str.contains(title, case=False, regex=False)].sort_values(
        ["title", "release_year"]
    )
    candidates = exact if not exact.empty else fuzzy
    if candidates.empty:
        raise ValueError(f"No movie matched title: {title}")
    return candidates.iloc[0]


def build_normalization_stats(payload: pd.DataFrame) -> dict[str, float]:
    numeric_columns = [
        "vote_average",
        "vote_count",
        "popularity",
        "recommendation_quality_score",
    ]
    for column in numeric_columns:
        payload[column] = pd.to_numeric(payload[column], errors="coerce").fillna(0.0)

    return {
        "max_vote_average": max(float(payload["vote_average"].max()), 1.0),
        "max_vote_count": max(float(payload["vote_count"].max()), 1.0),
        "max_popularity": max(float(payload["popularity"].max()), 1.0),
        "max_quality": max(float(payload["recommendation_quality_score"].max()), 1.0),
    }


def calculate_hybrid_scores(
    rows: list[dict[str, Any]],
    normalization_stats: dict[str, float],
) -> list[dict[str, Any]]:
    scored_rows = []
    for row in rows:
        rating_norm = float(row.get("vote_average") or 0.0) / normalization_stats[
            "max_vote_average"
        ]
        vote_count_norm = float(row.get("vote_count") or 0.0) / normalization_stats[
            "max_vote_count"
        ]
        popularity_norm = float(row.get("popularity") or 0.0) / normalization_stats[
            "max_popularity"
        ]
        quality_norm = float(
            row.get("recommendation_quality_score") or 0.0
        ) / normalization_stats["max_quality"]

        hybrid_score = (
            HYBRID_WEIGHTS["similarity_score"] * float(row["similarity_score"])
            + HYBRID_WEIGHTS["rating_norm"] * rating_norm
            + HYBRID_WEIGHTS["vote_count_norm"] * vote_count_norm
            + HYBRID_WEIGHTS["popularity_norm"] * popularity_norm
            + HYBRID_WEIGHTS["quality_norm"] * quality_norm
        )

        scored_row = {
            **row,
            "rating_norm": rating_norm,
            "vote_count_norm": vote_count_norm,
            "popularity_norm": popularity_norm,
            "quality_norm": quality_norm,
            "hybrid_score": hybrid_score,
        }
        scored_rows.append(scored_row)

    scored_rows.sort(
        key=lambda item: (
            item["hybrid_score"],
            item["similarity_score"],
            item.get("vote_count") or 0,
        ),
        reverse=True,
    )

    for rank, row in enumerate(scored_rows, start=1):
        row["hybrid_rank"] = rank
        row["rank"] = rank

    return scored_rows


def search_similar_movies(
    source: pd.Series,
    source_vector: list[float],
    top_k: int,
    candidate_k: int,
    normalization_stats: dict[str, float],
) -> list[dict[str, Any]]:
    response = qdrant_request(
        "POST",
        f"/collections/{QDRANT_COLLECTION}/points/search",
        json={
            "vector": source_vector,
            "limit": candidate_k + 1,
            "with_payload": True,
        },
    ).json()

    rows: list[dict[str, Any]] = []
    qdrant_rank = 1
    source_id = int(source["id"])

    for result in response.get("result", []):
        if int(result["id"]) == source_id:
            continue

        movie = result.get("payload", {})
        rows.append(
            {
                "query": source["title"],
                "source_id": source_id,
                "source_title": source["title"],
                "source_release_year": source.get("release_year"),
                "source_genres": source.get("genres_text"),
                "qdrant_rank": qdrant_rank,
                "recommended_id": int(result["id"]),
                "recommended_title": movie.get("title"),
                "recommended_release_year": movie.get("release_year"),
                "recommended_genres": movie.get("genres_text"),
                "vote_average": movie.get("vote_average"),
                "vote_count": movie.get("vote_count"),
                "popularity": movie.get("popularity"),
                "recommendation_quality_score": movie.get(
                    "recommendation_quality_score"
                ),
                "similarity_score": result.get("score"),
                "genre_overlap": genre_overlap(
                    source.get("genres_text"), movie.get("genres_text")
                ),
            }
        )
        qdrant_rank += 1

    return calculate_hybrid_scores(rows, normalization_stats)[:top_k]


def build_summary(examples: pd.DataFrame) -> pd.DataFrame:
    summary = (
        examples.groupby("query", as_index=False)
        .agg(
            recommendation_count=("recommended_id", "count"),
            avg_similarity_score=("similarity_score", "mean"),
            avg_hybrid_score=("hybrid_score", "mean"),
            avg_genre_overlap=("genre_overlap", "mean"),
            avg_vote_average=("vote_average", "mean"),
            avg_vote_count=("vote_count", "mean"),
        )
        .round(
            {
                "avg_similarity_score": 4,
                "avg_hybrid_score": 4,
                "avg_genre_overlap": 4,
                "avg_vote_average": 4,
                "avg_vote_count": 4,
            }
        )
    )

    overall = pd.DataFrame(
        [
            {
                "query": "__overall__",
                "recommendation_count": int(examples["recommended_id"].count()),
                "avg_similarity_score": round(examples["similarity_score"].mean(), 4),
                "avg_hybrid_score": round(examples["hybrid_score"].mean(), 4),
                "avg_genre_overlap": round(examples["genre_overlap"].mean(), 4),
                "avg_vote_average": round(examples["vote_average"].mean(), 4),
                "avg_vote_count": round(examples["vote_count"].mean(), 4),
            }
        ]
    )

    return pd.concat([summary, overall], ignore_index=True)


def main() -> None:
    if not VECTOR_PATH.exists():
        raise FileNotFoundError(f"Vector file not found: {VECTOR_PATH}")
    if not PAYLOAD_PATH.exists():
        raise FileNotFoundError(f"Payload file not found: {PAYLOAD_PATH}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    qdrant_request("GET", "/")

    vectors = pd.read_parquet(VECTOR_PATH, columns=["id", "vector"])
    vectors["id"] = pd.to_numeric(vectors["id"], errors="coerce").astype("int64")

    payload = pd.read_csv(PAYLOAD_PATH)
    payload["id"] = pd.to_numeric(payload["id"], errors="coerce").astype("int64")
    normalization_stats = build_normalization_stats(payload)

    all_rows: list[dict[str, Any]] = []
    top_k = int(os.getenv("EVALUATION_TOP_K", "10"))
    candidate_k = int(os.getenv("EVALUATION_CANDIDATE_K", "50"))

    for query in TEST_QUERIES:
        source = find_movie_by_title(payload, query)
        source_id = int(source["id"])
        source_vector = vectors.loc[vectors["id"] == source_id, "vector"]

        if source_vector.empty:
            print(f"Skipped {query}: vector not found for id={source_id}")
            continue

        rows = search_similar_movies(
            source=source,
            source_vector=[float(value) for value in source_vector.iloc[0]],
            top_k=top_k,
            candidate_k=candidate_k,
            normalization_stats=normalization_stats,
        )
        all_rows.extend(rows)
        print(f"Evaluated {query}: {len(rows)} recommendations")

    examples = pd.DataFrame(all_rows)
    summary = build_summary(examples)

    examples.to_csv(RECOMMENDATION_EXAMPLES_OUTPUT, index=False)
    summary.to_csv(MODEL_EVALUATION_SUMMARY_OUTPUT, index=False)

    print(f"Saved examples : {RECOMMENDATION_EXAMPLES_OUTPUT}")
    print(f"Saved summary  : {MODEL_EVALUATION_SUMMARY_OUTPUT}")
    print(f"Total rows     : {len(examples):,}")


if __name__ == "__main__":
    main()
