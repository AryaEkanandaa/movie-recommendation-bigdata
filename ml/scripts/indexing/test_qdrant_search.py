"""
Smoke test Qdrant vector search using an existing movie title.

Example:
docker compose run --rm ml python ml/scripts/indexing/test_qdrant_search.py "Interstellar"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ML_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ML_DIR / "data" / "processed"
VECTOR_PATH = PROCESSED_DIR / "vectors" / "movie_vectors_word2vec.parquet"
PAYLOAD_PATH = PROCESSED_DIR / "final" / "movies_payload.csv"

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "movies")
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"


def qdrant_request(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{QDRANT_URL}{path}"
    response = requests.request(method, url, timeout=120, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Qdrant request failed: {method} {url} "
            f"status={response.status_code} body={response.text[:500]}"
        )
    return response


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "Interstellar"
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    vectors = pd.read_parquet(VECTOR_PATH)
    payload = pd.read_csv(PAYLOAD_PATH, usecols=["id", "title", "release_year"])

    payload["id"] = pd.to_numeric(payload["id"], errors="coerce").astype("int64")
    vectors["id"] = pd.to_numeric(vectors["id"], errors="coerce").astype("int64")

    titles = payload["title"].fillna("")
    exact_candidates = payload[titles.str.lower() == query.lower()].sort_values(
        ["title", "release_year"]
    )
    fuzzy_candidates = payload[
        titles.str.contains(query, case=False, regex=False)
    ].sort_values(["title", "release_year"])
    candidates = exact_candidates if not exact_candidates.empty else fuzzy_candidates

    if candidates.empty:
        raise ValueError(f"No local movie title matched query: {query}")

    source = candidates.iloc[0]
    source_id = int(source["id"])
    source_vector = vectors.loc[vectors["id"] == source_id, "vector"]
    if source_vector.empty:
        raise ValueError(f"Vector not found for movie id: {source_id}")

    response = qdrant_request(
        "POST",
        f"/collections/{QDRANT_COLLECTION}/points/search",
        json={
            "vector": [float(value) for value in source_vector.iloc[0]],
            "limit": top_k + 1,
            "with_payload": True,
        },
    ).json()

    print(
        f"Source: {source['title']} ({int(source['release_year'])}) "
        f"[id={source_id}]"
    )
    print()
    print("Recommendations:")

    rank = 1
    for result in response.get("result", []):
        if int(result["id"]) == source_id:
            continue
        movie = result.get("payload", {})
        title = movie.get("title", "Unknown")
        year = movie.get("release_year", "N/A")
        genres = movie.get("genres_text", "")
        score = result.get("score", 0.0)
        print(f"{rank}. {title} ({year}) score={score:.4f} genres={genres}")
        rank += 1
        if rank > top_k:
            break


if __name__ == "__main__":
    main()
