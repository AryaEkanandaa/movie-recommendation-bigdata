# ML Workspace

Folder ini berisi pekerjaan machine learning untuk sistem rekomendasi film.

## Struktur

- `notebooks/`: eksplorasi data, preprocessing, dan modelling.
- `scripts/`: script Python yang bisa dijalankan ulang.
- `src/`: konfigurasi dan kode pendukung bersama.
- `reports/`: output analisis yang layak dibagikan, seperti gambar dan ringkasan CSV.

## Data

Dataset lokal disimpan di `ml/data/` dan tidak di-push ke GitHub karena ukurannya besar. Jika perlu menjalankan ulang pipeline, generate ulang data lewat script di `scripts/` atau letakkan dataset lokal di struktur `ml/data/`.

## Docker

Setup Docker tahap awal menyediakan:

- `ml`: environment Python + PySpark untuk menjalankan script/notebook ML.
- `qdrant`: vector database untuk tahap rekomendasi berikutnya.

Langkah awal:

```bash
cp .env.example .env
docker compose up -d qdrant
docker compose run --rm ml bash
```

Di dalam container `ml`, folder project tersedia di `/workspace`.

Catatan:

- Isi `TMDB_BEARER_TOKEN` di `.env` jika ingin menjalankan scraping/enrichment.
- Dataset besar tetap disimpan lokal di `ml/data/` dan tidak di-push ke GitHub.
- Storage Qdrant disimpan lokal di `qdrant_storage/` dan juga tidak di-push.

## Finalisasi Dataset

Sebelum training model lanjutan atau indexing ke Qdrant, generate dataset final:

```bash
python ml/scripts/preprocessing/finalize_datasets.py
```

Output:

- `ml/data/processed/movies_final.csv`: dataset utama untuk modelling.
- `ml/data/processed/movies_payload.csv`: metadata ringkas untuk backend/Qdrant payload.
- `ml/reports/data/data_summary.csv`: ringkasan kualitas dataset.

## Training Word2Vec

Setelah dataset final tersedia, train vector dense untuk Qdrant:

```bash
docker compose run --rm ml python ml/scripts/modelling/train_word2vec.py
```

Output:

- `ml/models/recommendation/word2vec_model/`: model Word2Vec lokal.
- `ml/data/processed/movie_vectors_word2vec.parquet`: vector film untuk Qdrant.
- `ml/reports/modelling/word2vec_summary.csv`: ringkasan training.

## Indexing Ke Qdrant

Setelah vector Word2Vec tersedia dan Qdrant berjalan, masukkan film ke collection `movies`:

```bash
docker compose run --rm ml python ml/scripts/indexing/index_qdrant.py
```

Script ini membaca:

- `ml/data/processed/movie_vectors_word2vec.parquet`
- `ml/data/processed/movies_payload.csv`

Lalu membuat/mengisi collection Qdrant:

- `movies`

Smoke test rekomendasi dari Qdrant:

```bash
docker compose run --rm ml python ml/scripts/indexing/test_qdrant_search.py "Interstellar"
```
