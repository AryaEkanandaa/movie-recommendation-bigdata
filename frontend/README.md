# CineMatch Frontend

Frontend React untuk chatbot rekomendasi film.

## Fitur

- Chat input berbasis judul film.
- Prompt suggestions.
- Pilihan kandidat ketika judul ambigu.
- Poster dan metadata film dari TMDB payload.
- Similarity score dari Word2Vec/Qdrant.
- Pemahaman bahasa natural dan alasan rekomendasi dari OpenAI ketika API key tersedia.
- Pencarian gabungan berdasarkan genre, aktor, sutradara, keyword, bahasa, rating, tahun, dan durasi.
- Metadata discovery tanpa harus menyebut film acuan.
- Fallback otomatis ke parser judul ketika OpenAI belum dikonfigurasi atau sedang gagal.
- Loading, empty, offline, dan error states.
- Responsive desktop dan mobile.

## Menjalankan Dengan Docker

```bash
docker compose up -d --build frontend
```

Buka:

```text
http://localhost:3000
```

Frontend mengakses backend melalui `VITE_API_BASE_URL`, default `http://localhost:8000`.
