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
| Export `data/processed/movies_final.csv` | Not started | Belum ada `data/processed/` | Jangan ulang preprocessing penuh; cukup buat export final dari CSV yang sudah ada. |
| Export `data/processed/movies_payload.csv` | Not started | Belum ada | Dibutuhkan untuk Qdrant payload/backend. |
| Buat `reports/data/data_summary.csv` | Not started | Belum ada `reports/data/` | Bisa dibuat dari dataset final. |

## Modelling

| Task | Status | Bukti | Catatan |
| --- | --- | --- | --- |
| CountVectorizer baseline | Done | `notebooks/MODELLING.ipynb` | Sudah ada fungsi rekomendasi. |
| TF-IDF + Cosine Similarity | Done | `notebooks/MODELLING.ipynb` | Sudah ada sebagai model utama notebook. |
| K-Means clustering | Done | `notebooks/MODELLING.ipynb` | Sudah ada cluster summary dan top terms. |
| Hybrid ranking | Partial | `notebooks/MODELLING.ipynb` | Sudah ada, tetapi perlu mapping kolom dataset terbaru. |
| Evaluation test cases | Partial | `notebooks/MODELLING.ipynb` | Sudah ada 5 query; docs meminta lebih lengkap. |
| Export `recommendation_examples.csv` | Partial | Ada code export di notebook | File output belum terlihat di `reports/modelling/` pada repo saat ini. |
| Export `model_comparison_summary.csv` | Partial | Ada code export di notebook | File output belum terlihat di `reports/modelling/`. |
| Export `kmeans_cluster_summary.csv` | Partial | Ada code export di notebook | File output belum terlihat di `reports/modelling/`. |
| Word2Vec dense vector | Not started | Belum ada cell/heading Word2Vec | Ini masih perlu dibuat untuk Qdrant MVP. |
| Export dense vectors | Not started | Belum ada `movie_vectors_word2vec.parquet` | Dibutuhkan untuk indexing Qdrant. |

## Vector Database

| Task | Status | Bukti | Catatan |
| --- | --- | --- | --- |
| Qdrant setup | Not started | Belum ada docker compose/script Qdrant | Masih perlu dibuat. |
| Collection `movies` | Not started | Belum ada script index | Masih perlu dibuat. |
| Index vector film | Not started | Belum ada `scripts/index_qdrant.py` | Menunggu Word2Vec/dense vector. |
| Test vector search | Not started | Belum ada | Masih perlu dibuat. |
| Test metadata payload | Not started | Belum ada | Masih perlu dibuat. |

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
| Model evaluation doc | Not started | Belum ada `docs/MODEL_EVALUATION.md` | Menunggu output evaluasi final. |
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

1. Perbaiki `MODELLING.ipynb` agar path dan nama kolom cocok dengan dataset terbaru.
2. Jalankan ulang modelling sampai file `reports/modelling/*.csv` benar-benar muncul.
3. Tambahkan Word2Vec untuk menghasilkan dense vector.
4. Export dataset final dan payload:
   - `data/processed/movies_final.csv`
   - `data/processed/movies_payload.csv`
   - `data/processed/movie_vectors_word2vec.parquet`
5. Setup Qdrant dan script indexing.
6. Buat FastAPI.
7. Buat Streamlit chatbot.

