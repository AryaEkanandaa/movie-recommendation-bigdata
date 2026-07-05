# Frontend Setup

Frontend menggunakan React + Vite dan disajikan oleh Nginx dalam Docker.

## Menjalankan Aplikasi

Pastikan Qdrant sudah memiliki collection `movies`, lalu jalankan:

```bash
docker compose up -d --build frontend
```

Docker Compose otomatis menjalankan dependency:

- Qdrant di `http://localhost:6333`
- FastAPI di `http://localhost:8000`
- CineMatch frontend di `http://localhost:3000`

## Alur Request

```text
User chat
-> React frontend
-> FastAPI /chat
-> Qdrant vector search
-> hybrid re-ranking
-> recommendation cards
```

## Development Lokal

```bash
cd frontend
npm install
npm run dev
```

Vite development server tersedia di `http://localhost:5173`.
