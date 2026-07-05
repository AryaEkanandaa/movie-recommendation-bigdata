# ML Workspace

Folder ini berisi pekerjaan machine learning untuk sistem rekomendasi film.

## Struktur

- `notebooks/`: eksplorasi data, preprocessing, dan modelling.
- `scripts/`: script Python yang bisa dijalankan ulang.
- `src/`: konfigurasi dan kode pendukung bersama.
- `reports/`: output analisis yang layak dibagikan, seperti gambar dan ringkasan CSV.

## Data

Dataset lokal disimpan di `ml/data/` dan tidak di-push ke GitHub karena ukurannya besar. Jika perlu menjalankan ulang pipeline, generate ulang data lewat script di `scripts/` atau letakkan dataset lokal di struktur `ml/data/`.

Struktur data lokal:

- `ml/data/curated/`: dataset input yang sudah diperkaya dan siap dipakai pipeline final.
- `ml/data/processed/final/`: dataset final dan payload aplikasi.
- `ml/data/processed/vectors/`: vector/embedding film hasil model.

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

- `ml/data/processed/final/movies_final.csv`: dataset utama untuk modelling.
- `ml/data/processed/final/movies_payload.csv`: metadata ringkas untuk backend/Qdrant payload.
- `ml/reports/data/data_summary.csv`: ringkasan kualitas dataset.

## Training Word2Vec

Setelah dataset final tersedia, train vector dense untuk Qdrant:

```bash
docker compose run --rm ml python ml/scripts/modelling/train_word2vec.py
```

Output:

- `ml/models/recommendation/word2vec_model/`: model Word2Vec lokal.
- `ml/data/processed/vectors/movie_vectors_word2vec.parquet`: vector film untuk Qdrant.
- `ml/reports/modelling/training/word2vec_summary.csv`: ringkasan training.

## Indexing Ke Qdrant

Setelah vector Word2Vec tersedia dan Qdrant berjalan, masukkan film ke collection `movies`:

```bash
docker compose run --rm ml python ml/scripts/indexing/index_qdrant.py
```

Script ini membaca:

- `ml/data/processed/vectors/movie_vectors_word2vec.parquet`
- `ml/data/processed/final/movies_payload.csv`

Lalu membuat/mengisi collection Qdrant:

- `movies`

Smoke test rekomendasi dari Qdrant:

```bash
docker compose run --rm ml python ml/scripts/indexing/test_qdrant_search.py "Interstellar"
```

Setelah indexing selesai, backend FastAPI dapat dijalankan dengan:

```bash
docker compose up -d backend
```

Dokumentasi endpoint tersedia di `docs/BACKEND_API.md`.

## Evaluasi Rekomendasi

Setelah Qdrant terisi, jalankan evaluasi contoh rekomendasi:

```bash
docker compose run --rm ml python ml/scripts/modelling/evaluate_recommendations.py
```

Output:

- `ml/reports/modelling/evaluation/recommendation_examples.csv`
- `ml/reports/modelling/evaluation/model_evaluation_summary.csv`

Notebook pendukung presentasi:

- `ml/notebooks/EVALUATION.ipynb`

## Perbandingan Model

Untuk membandingkan CountVectorizer, TF-IDF, dan Word2Vec + Qdrant:

```bash
docker compose run --rm ml python ml/scripts/modelling/compare_text_models.py
```

Output:

- `ml/reports/modelling/comparison/model_comparison_examples.csv`
- `ml/reports/modelling/comparison/model_comparison_summary.csv`
