# Docker Setup

Dokumen ini menjelaskan cara menjalankan environment awal project dengan Docker.

## Prasyarat

- Docker Desktop atau OrbStack sudah terinstall dan sedang berjalan.
- File dataset besar tersedia secara lokal di `ml/data/` jika ingin menjalankan proses ML yang membaca dataset.

## Setup Awal

Copy contoh environment:

```bash
cp .env.example .env
```

Isi `TMDB_BEARER_TOKEN` di `.env` jika ingin menjalankan scraping atau enrichment data.

## Menjalankan Qdrant

Qdrant adalah vector database yang nanti dipakai untuk similarity search.

```bash
docker compose up -d qdrant
```

Qdrant REST API akan tersedia di:

```text
http://localhost:6333
```

Storage Qdrant akan disimpan lokal di `qdrant_storage/` dan tidak di-push ke GitHub.

## Masuk Ke Environment ML

Build dan masuk ke container ML:

```bash
docker compose run --rm ml bash
```

Di dalam container, project tersedia di:

```text
/workspace
```

Contoh cek Python:

```bash
python --version
python -c "import pandas, pyspark; print('ML environment OK')"
```

## Perintah Berguna

Melihat service yang berjalan:

```bash
docker compose ps
```

Melihat log Qdrant:

```bash
docker compose logs qdrant
```

Menghentikan service:

```bash
docker compose down
```

Menghapus container dan network, tetapi tetap menyimpan data Qdrant lokal:

```bash
docker compose down
```

## Catatan Untuk Tim

- Jangan commit `.env`.
- Jangan commit `ml/data/`.
- Jangan commit `qdrant_storage/`.
- Backend dan frontend belum dimasukkan ke Docker Compose karena aplikasinya belum dibuat.
