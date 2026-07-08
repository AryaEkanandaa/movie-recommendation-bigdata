# Start Here - Movie Recommendation Chatbot

Dokumen ini adalah titik awal untuk melanjutkan project dari fase sekarang.

## Status Project Saat Ini

Project sudah memiliki fondasi utama:

- Dataset final sekitar 80 ribu film.
- File utama:
  - `data/tmdb_movie_documents.csv`
  - `data/tmdb_movies_model_ready.csv`
- Notebook EDA:
  - `notebooks/EDA.ipynb`
- Notebook preprocessing:
  - `notebooks/PREPROCESSING.ipynb`
- Notebook modelling:
  - `notebooks/MODELLING.ipynb`
- Script scraping dan enrichment TMDB:
  - `scripts/scraping/fetch_tmdb_movies.py`
  - `scripts/scraping/enrich_tmdb_movies.py`

Target berikutnya adalah mengubah hasil notebook menjadi aplikasi chatbot rekomendasi film.

## Tujuan Akhir

Aplikasi berbentuk chatbot. User bisa menulis pertanyaan seperti:

```text
Rekomendasi film selain Interstellar
Film yang mirip Inception tapi lebih ringan
Carikan film drama Korea dengan rating bagus
Rekomendasi film action tahun 2010-an
```

Sistem akan:

1. Memahami maksud pertanyaan user.
2. Mencari film acuan atau kriteria filter.
3. Mengambil kandidat film dari model rekomendasi.
4. Melakukan ranking ulang dengan skor hybrid.
5. Menghasilkan jawaban natural berisi daftar film dan alasan rekomendasi.

## Prinsip Utama

Model rekomendasi adalah komponen utama. LLM hanya digunakan sebagai antarmuka percakapan dan pembuat penjelasan.

Dengan kata lain:

```text
Model rekomendasi -> menentukan film
LLM chatbot       -> menjelaskan hasil ke user
```

## MVP Yang Akan Dibangun

MVP adalah versi minimum yang bisa didemokan:

- User bisa bertanya lewat chatbot.
- Sistem bisa mencari film mirip berdasarkan judul.
- Sistem bisa memberi 5-10 rekomendasi.
- Rekomendasi berasal dari model yang dilatih sendiri dari metadata film.
- Hasil rekomendasi disimpan dan dicari lewat vector database.
- Jawaban chatbot berisi alasan singkat untuk setiap film.

## Stack Rekomendasi

Untuk MVP:

- Model training: PySpark ML
- Model utama: TF-IDF + Cosine Similarity
- Model pembanding: Word2Vec
- Ranking final: Hybrid Ranking
- Vector DB: Qdrant
- Backend: FastAPI
- Frontend cepat: Streamlit
- Frontend lebih rapi: React atau Next.js

Rekomendasi paling realistis untuk mulai:

```text
PySpark model -> Qdrant -> FastAPI -> Streamlit
```

## Urutan Kerja Singkat

1. Finalisasi dataset model.
2. Train TF-IDF dan Word2Vec.
3. Evaluasi rekomendasi.
4. Simpan vector ke Qdrant.
5. Buat backend FastAPI.
6. Buat chatbot UI.
7. Buat dokumentasi laporan dan presentasi.

Detail teknis ada di:

- `docs/MVP_PLAN.md`
- `docs/TASK_BREAKDOWN.md`
- `docs/PRESENTATION_QA.md`
