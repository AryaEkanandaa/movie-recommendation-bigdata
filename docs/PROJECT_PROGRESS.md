# Project Progress - Avoid Double Work

Dokumen ini mencocokkan rencana di `docs/TASK_BREAKDOWN.md` dengan kondisi repo saat ini.

Status:

- Done: sudah ada dan tidak perlu dikerjakan ulang dari nol.
- Partial: sudah ada sebagian, tetapi perlu dirapikan/diperbaiki agar cocok dengan MVP.
- Not started: belum terlihat di repo.

## Data

| Task | Status | Bukti | Catatan |
| --- | --- | --- | --- |
| Dataset film tersedia | Done | `data/tmdb_movie_documents.csv`, `data/tmdb_movies_model_ready.csv` | Sekitar 80 ribu film. |
| EDA | Done | `notebooks/EDA.ipynb`, `reports/figures/` | Grafik dan analisis EDA sudah ada. |
| Preprocessing | Done | `notebooks/PREPROCESSING.ipynb`, `reports/preprocessing/preprocessing_summary.csv` | Dataset hasil preprocessing sudah muncul di folder `data/`. |
| Validasi duplicate/kosong | Partial | Ada di notebook preprocessing/modelling | Perlu dibuat ringkas sebagai output final jika ingin laporan rapi. |
| Export `data/processed/movies_final.csv` | Done | `ml/scripts/preprocessing/finalize_datasets.py` | Output lokal ada di `ml/data/processed/movies_final.csv` dan tidak di-push. |
| Export `data/processed/movies_payload.csv` | Done | `ml/scripts/preprocessing/finalize_datasets.py` | Output lokal ada di `ml/data/processed/movies_payload.csv` dan tidak di-push. |
| Buat `reports/data/data_summary.csv` | Done | `ml/reports/data/data_summary.csv` | Ringkasan final dataset sudah dibuat. |

## Modelling

| Task | Status | Bukti | Catatan |
| --- | --- | --- | --- |
| CountVectorizer baseline | Done | `notebooks/MODELLING.ipynb` | Sudah ada fungsi rekomendasi. |
| TF-IDF + Cosine Similarity | Done | `notebooks/MODELLING.ipynb` | Sudah ada sebagai model utama notebook. |
| K-Means clustering | Done | `notebooks/MODELLING.ipynb` | Sudah ada cluster summary dan top terms. |
| Hybrid ranking | Partial | `notebooks/MODELLING.ipynb` | Sudah ada, tetapi perlu mapping kolom dataset terbaru. |
| Evaluation test cases | Done | `ml/scripts/modelling/evaluate_recommendations.py`, `ml/reports/modelling/model_evaluation_summary.csv` | 9 query x 10 rekomendasi sudah dievaluasi. |
| Export `recommendation_examples.csv` | Done | `ml/reports/modelling/recommendation_examples.csv` | 90 baris contoh rekomendasi sudah dibuat. |
| Export `model_comparison_summary.csv` | Partial | `ml/notebooks/MODELLING.ipynb`, `docs/MODEL_EVALUATION.md` | Pembanding CountVectorizer/TF-IDF dijelaskan sebagai baseline; summary CSV pembanding lama belum digenerate ulang. |
| Export `kmeans_cluster_summary.csv` | Partial | Ada code export di notebook | File output belum terlihat di `reports/modelling/`. |
| Word2Vec dense vector | Done | `ml/scripts/modelling/train_word2vec.py` | Vector size 64, vocabulary 82.793, total 80.290 film. |
| Export dense vectors | Done | `ml/data/processed/movie_vectors_word2vec.parquet` | Output lokal di-ignore karena besar. |

## Vector Database

| Task | Status | Bukti | Catatan |
| --- | --- | --- | --- |
| Qdrant setup | Done | `docker-compose.yml` | Qdrant berjalan di `localhost:6333`. |
| Collection `movies` | Done | `ml/scripts/indexing/index_qdrant.py` | Collection dibuat dengan vector size 64 dan distance cosine. |
| Index vector film | Done | `ml/scripts/indexing/index_qdrant.py` | 80.290 film berhasil di-index ke Qdrant lokal. |
| Test vector search | Done | `ml/scripts/indexing/test_qdrant_search.py` | Query `Interstellar` mengembalikan rekomendasi sci-fi seperti `The Martian` dan `Arrival`. |
| Test metadata payload | Partial | `ml/scripts/indexing/test_qdrant_search.py` | Payload title/year/genre terbaca; validasi backend belum dibuat. |

## Backend

| Task | Status | Bukti | Catatan |
| --- | --- | --- | --- |
| FastAPI setup | Not started | Belum ada folder `app/backend` | Masih perlu dibuat. |
| Endpoint `/health` | Not started | Belum ada | Masih perlu dibuat. |
| Endpoint `/movies/search` | Not started | Belum ada | Masih perlu dibuat. |
| Endpoint `/recommend/similar` | Not started | Belum ada | Masih perlu dibuat. |
| Endpoint `/chat` | Not started | Belum ada | Masih perlu dibuat. |

## Frontend

| Task | Status | Bukti | Catatan |
| --- | --- | --- | --- |
| Streamlit setup | Not started | Belum ada folder `app/frontend` | Masih perlu dibuat. |
| Chat input | Not started | Belum ada | Masih perlu dibuat. |
| Recommendation card | Not started | Belum ada | Masih perlu dibuat. |
| Loading/error state | Not started | Belum ada | Masih perlu dibuat. |

## Documentation

| Task | Status | Bukti | Catatan |
| --- | --- | --- | --- |
| Start guide | Done | `docs/START_HERE.md` | Sudah ada. |
| MVP plan | Done | `docs/MVP_PLAN.md` | Sudah ada. |
| Task breakdown | Done | `docs/TASK_BREAKDOWN.md` | Sudah ada. |
| Progress tracker | Done | `docs/PROJECT_PROGRESS.md` | Dokumen ini. |
| README | Not started | Belum ada `README.md` | Perlu dibuat setelah struktur MVP fix. |
| Architecture doc | Not started | Belum ada `docs/ARCHITECTURE.md` | Bisa dibuat setelah backend/Qdrant diputuskan. |
| Model evaluation doc | Done | `docs/MODEL_EVALUATION.md` | Menjelaskan model, library, Qdrant, dan cara evaluasi. |
| Demo script | Not started | Belum ada `docs/DEMO_SCRIPT.md` | Menunggu aplikasi MVP. |

## Jangan Dikerjakan Ulang Dari Nol

Bagian ini sudah ada dan cukup dilanjutkan/dirapikan:

1. Scraping TMDB.
2. Enrichment TMDB.
3. EDA.
4. Preprocessing.
5. Pembuatan `movie_document_weighted`.
6. CountVectorizer baseline.
7. TF-IDF recommendation.
8. K-Means clustering.
9. Draft hybrid ranking.

## Fokus Berikutnya

Urutan kerja paling aman dari kondisi sekarang:

1. Buat FastAPI backend:
   - `/health`
   - `/movies/search`
   - `/recommend/similar`
2. Pindahkan logic search/recommendation dari script smoke test ke backend.
3. Tambahkan hybrid re-ranking di backend.
4. Buat Streamlit chatbot.
5. Buat dokumentasi evaluasi model dan demo script.
