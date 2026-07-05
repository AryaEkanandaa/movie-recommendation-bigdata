# Backend API

Backend ini menggunakan FastAPI untuk menghubungkan frontend dengan Qdrant.

## Struktur

- `app/main.py`: endpoint FastAPI dan lifecycle aplikasi.
- `app/recommender.py`: pencarian judul, Qdrant similarity search, dan hybrid re-ranking.
- `app/qdrant_gateway.py`: client REST untuk Qdrant.
- `app/schemas.py`: bentuk request dan response API.
- `tests/`: unit test helper backend.

## Jalankan

```bash
docker compose up -d qdrant backend
```

Buka dokumentasi interaktif di:

```text
http://localhost:8000/docs
```

Dokumentasi endpoint lengkap ada di `docs/BACKEND_API.md`.
