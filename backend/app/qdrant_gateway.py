from __future__ import annotations

from typing import Any

import requests

from .config import Settings


class QdrantGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.settings.qdrant_url}{path}",
            timeout=self.settings.qdrant_timeout_seconds,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/")

    def collection_info(self) -> dict[str, Any]:
        return self._request("GET", f"/collections/{self.settings.qdrant_collection}")

    def get_vector(self, point_id: int) -> list[float]:
        response = self._request(
            "GET",
            f"/collections/{self.settings.qdrant_collection}/points/{point_id}?with_vector=true",
        )
        result = response.get("result") or {}
        vector = result.get("vector")
        if not vector:
            raise LookupError(f"Vector tidak ditemukan untuk movie id={point_id}.")
        return [float(value) for value in vector]

    def search(self, vector: list[float], limit: int) -> list[dict[str, Any]]:
        response = self._request(
            "POST",
            f"/collections/{self.settings.qdrant_collection}/points/search",
            json={"vector": vector, "limit": limit, "with_payload": True},
        )
        return response.get("result", [])
