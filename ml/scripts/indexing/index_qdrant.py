"""
Index Word2Vec movie vectors into Qdrant.

Inputs:
- ml/data/processed/movie_vectors_word2vec.parquet
- ml/data/processed/movies_payload.csv

Target:
- Qdrant collection: movies
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ML_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ML_DIR / "data" / "processed"

VECTOR_PATH = PROCESSED_DIR / "movie_vectors_word2vec.parquet"
PAYLOAD_PATH = PROCESSED_DIR / "movies_payload.csv"

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "movies")
QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_BATCH_SIZE", "512"))
QDRANT_RECREATE_COLLECTION = os.getenv("QDRANT_RECREATE_COLLECTION", "true").lower() in {
    "1",
    "true",
    "yes",
}

QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")


def qdrant_request(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{QDRANT_URL}{path}"
    response = requests.request(method, url, timeout=120, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Qdrant request failed: {method} {url} "
            f"status={response.status_code} body={response.text[:500]}"
        )
    return response


def clean_payload_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def build_payload(row: pd.Series, payload_columns: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for column in payload_columns:
        value = clean_payload_value(row[column])
        if value is not None:
            payload[column] = value
    return payload


def recreate_collection(vector_size: int) -> None:
    if QDRANT_RECREATE_COLLECTION:
        response = requests.delete(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}", timeout=120
        )
        if response.status_code not in {200, 404}:
            raise RuntimeError(
                f"Failed deleting collection: status={response.status_code} "
                f"body={response.text[:500]}"
            )

    qdrant_request(
        "PUT",
        f"/collections/{QDRANT_COLLECTION}",
        json={"vectors": {"size": vector_size, "distance": "Cosine"}},
    )


def upsert_points(points: list[dict[str, Any]]) -> None:
    qdrant_request(
        "PUT",
        f"/collections/{QDRANT_COLLECTION}/points?wait=true",
        json={"points": points},
    )


def main() -> None:
    require_file(VECTOR_PATH)
    require_file(PAYLOAD_PATH)

    qdrant_request("GET", "/")

    vectors = pd.read_parquet(VECTOR_PATH)
    payload = pd.read_csv(PAYLOAD_PATH)

    vectors["id"] = pd.to_numeric(vectors["id"], errors="coerce").astype("int64")
    payload["id"] = pd.to_numeric(payload["id"], errors="coerce").astype("int64")

    data = vectors[["id", "vector"]].merge(payload, on="id", how="inner")
    if data.empty:
        raise ValueError("No rows to index after merging vectors and payload.")

    first_vector = data.iloc[0]["vector"]
    vector_size = len(first_vector)
    payload_columns = [column for column in data.columns if column not in {"id", "vector"}]

    recreate_collection(vector_size)

    total_rows = len(data)
    for start in range(0, total_rows, QDRANT_BATCH_SIZE):
        batch = data.iloc[start : start + QDRANT_BATCH_SIZE]
        points = []

        for _, row in batch.iterrows():
            points.append(
                {
                    "id": int(row["id"]),
                    "vector": [float(value) for value in row["vector"]],
                    "payload": build_payload(row, payload_columns),
                }
            )

        upsert_points(points)
        end = min(start + QDRANT_BATCH_SIZE, total_rows)
        print(f"Indexed {end:,}/{total_rows:,} movies")

    collection = qdrant_request(
        "GET", f"/collections/{QDRANT_COLLECTION}"
    ).json()

    print(f"Collection          : {QDRANT_COLLECTION}")
    print(f"Vector size         : {vector_size}")
    print(f"Indexed movie count : {total_rows:,}")
    print(f"Qdrant status       : {collection.get('result', {}).get('status')}")


if __name__ == "__main__":
    main()
