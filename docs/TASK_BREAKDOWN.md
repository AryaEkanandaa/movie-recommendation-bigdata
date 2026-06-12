# Task Breakdown - Movie Recommendation Chatbot

Dokumen ini membagi pekerjaan ke beberapa role agar tim bisa mulai paralel.

## Ringkasan Role

Jika tim berisi 4 orang:

1. Data Engineer
2. ML Engineer
3. Backend Engineer
4. Frontend + Documentation

Jika tim berisi 5 orang, pisahkan Documentation menjadi role sendiri.

## Timeline MVP

Estimasi MVP realistis: 2-3 minggu.

```text
Week 1: data finalization + model training
Week 2: Qdrant + backend + evaluation
Week 3: chatbot UI + documentation + demo polishing
```

## Role 1 - Data Engineer

### Tanggung Jawab

Menyiapkan dataset final yang dipakai training dan aplikasi.

### Input

```text
data/tmdb_movie_documents.csv
data/tmdb_movies_model_ready.csv
```

### Task

- Cek jumlah baris dan duplikasi `id`.
- Cek kolom kosong pada `title`, `movie_document_weighted`, `genres_text`.
- Buang data yang tidak layak untuk rekomendasi.
- Pastikan tipe data numerik benar:
  - `release_year`
  - `runtime`
  - `vote_average`
  - `vote_count`
  - `popularity`
  - `recommendation_quality_score`
- Buat dataset final:
  - `data/processed/movies_final.csv`
- Buat dataset khusus aplikasi:
  - `data/processed/movies_payload.csv`
- Buat ringkasan data:
  - `reports/data/data_summary.csv`

### Output

```text
data/processed/movies_final.csv
data/processed/movies_payload.csv
reports/data/data_summary.csv
```

### Acceptance Criteria

- Tidak ada duplicate `id`.
- Tidak ada title kosong.
- Tidak ada `movie_document_weighted` kosong.
- Semua kolom numerik bisa dipakai scoring.
- Dataset final bisa dibaca oleh script training.

## Role 2 - ML Engineer

### Tanggung Jawab

Melatih model rekomendasi dan menyiapkan vector film.

### Input

```text
data/processed/movies_final.csv
```

### Task

#### A. TF-IDF Baseline

- Load dataset dengan PySpark.
- Tokenisasi `movie_document_weighted`.
- Stopword removal.
- Train CountVectorizer.
- Train IDF.
- Generate TF-IDF vector.
- Buat fungsi rekomendasi berbasis cosine similarity.

#### B. Word2Vec Model

- Gunakan token hasil preprocessing.
- Train Word2Vec dari corpus film.
- Generate dense vector setiap film.
- Simpan vector untuk indexing Qdrant.

#### C. Hybrid Ranking

- Buat normalisasi:
  - `rating_norm`
  - `vote_count_norm`
  - `popularity_norm`
  - `quality_norm`
- Buat formula final score.
- Test beberapa film acuan.

#### D. Evaluation

- Jalankan test case:
  - Interstellar
  - Inception
  - The Dark Knight
  - Titanic
  - Toy Story
  - Parasite
  - La La Land
  - Spirited Away
- Hitung:
  - genre overlap
  - keyword overlap
  - average rating
  - average vote count
  - average final score
- Bandingkan TF-IDF dan Word2Vec.

### Output

```text
models/recommendation/tfidf_model/
models/recommendation/word2vec_model/
data/processed/movie_vectors_word2vec.parquet
reports/modelling/recommendation_examples.csv
reports/modelling/model_comparison_summary.csv
```

### Acceptance Criteria

- Model bisa menghasilkan top 10 rekomendasi dari judul film.
- Ada minimal 8 test case.
- Ada hasil perbandingan model.
- Ada vector dense untuk Qdrant.

## Role 3 - Vector Database + Backend Engineer

### Tanggung Jawab

Menyiapkan Qdrant dan API rekomendasi.

### Input

```text
data/processed/movie_vectors_word2vec.parquet
data/processed/movies_payload.csv
```

### Task

#### A. Qdrant Setup

- Jalankan Qdrant via Docker.
- Buat collection `movies`.
- Tentukan vector size sesuai output Word2Vec.
- Insert vector + payload.
- Buat script re-indexing.

#### B. Movie Search

- Buat fungsi exact title search.
- Buat fungsi case-insensitive title search.
- Tambahkan fuzzy matching jika perlu.

#### C. Recommendation API

Backend menggunakan FastAPI.

Endpoint:

```text
GET /health
GET /movies/search?title=
GET /recommend/similar?title=&top_k=
POST /chat
```

#### D. Hybrid Re-ranking

- Ambil kandidat dari Qdrant.
- Hitung final score.
- Sort descending.
- Return top N.

### Output

```text
app/backend/main.py
app/backend/recommender.py
app/backend/qdrant_client.py
app/backend/schemas.py
scripts/index_qdrant.py
```

### Acceptance Criteria

- `/health` mengembalikan status OK.
- `/movies/search` bisa menemukan film.
- `/recommend/similar` mengembalikan rekomendasi.
- `/chat` mengembalikan jawaban dan list recommendation.
- Response time lokal masih nyaman untuk demo.

## Role 4 - Frontend Engineer

### Tanggung Jawab

Membuat antarmuka chatbot.

### MVP Frontend Option

Gunakan Streamlit agar cepat.

### Task

- Buat halaman chat.
- Buat input message.
- Tampilkan response assistant.
- Tampilkan recommendation card.
- Tampilkan error jika film tidak ditemukan.
- Tambahkan contoh prompt.

### Output

```text
app/frontend/streamlit_app.py
```

### Recommendation Card

Isi card:

- title
- release_year
- genres
- vote_average
- reason

Opsional:

- poster dari `poster_path`
- overview pendek

### Acceptance Criteria

- User bisa mengetik pertanyaan.
- Frontend memanggil endpoint backend.
- Rekomendasi tampil rapi.
- Ada loading state.
- Ada error state.

## Role 5 - Documentation + Presentation

Jika hanya 4 orang, role ini bisa dipegang Frontend atau dibagi ke semua anggota.

### Tanggung Jawab

Menyiapkan laporan, README, dan bahan presentasi.

### Task

- Jelaskan dataset.
- Jelaskan preprocessing.
- Jelaskan alasan content-based recommendation.
- Jelaskan kenapa ALS/collaborative filtering tidak dipakai.
- Jelaskan model yang dilatih:
  - TF-IDF
  - Word2Vec
  - Hybrid Ranking
- Jelaskan kenapa pakai Qdrant.
- Jelaskan konsep RAG dalam chatbot.
- Masukkan hasil evaluasi.
- Ambil screenshot aplikasi.
- Buat narasi demo.

### Output

```text
README.md
docs/ARCHITECTURE.md
docs/MODEL_EVALUATION.md
docs/DEMO_SCRIPT.md
```

### Acceptance Criteria

- Laporan menjelaskan end-to-end pipeline.
- Ada diagram arsitektur.
- Ada hasil evaluasi model.
- Ada screenshot aplikasi.
- Ada script demo 3-5 menit.

## Backlog Teknis

### P0 - Wajib Untuk MVP

- Final dataset bersih.
- TF-IDF baseline.
- Word2Vec vector.
- Qdrant indexing.
- FastAPI `/recommend/similar`.
- Chatbot UI sederhana.
- Laporan evaluasi.

### P1 - Bagus Jika Sempat

- Fuzzy title matching.
- Genre/year/language filter.
- Poster film.
- Chat history.
- LLM-based intent parser.
- Docker Compose untuk backend + Qdrant.

### P2 - Lanjutan

- User login.
- Favorite movies.
- Personalized recommendation.
- Feedback like/dislike.
- Fine-tuning ranking weight dari feedback user.
- PostgreSQL + pgvector.

## Task Board Awal

Gunakan checklist ini sebagai task board.

### Data

- [ ] Buat folder `data/processed`.
- [ ] Validasi duplicate `id`.
- [ ] Validasi kolom kosong.
- [ ] Export `movies_final.csv`.
- [ ] Export `movies_payload.csv`.
- [ ] Buat `data_summary.csv`.

### Modelling

- [ ] Train TF-IDF.
- [ ] Buat cosine similarity function.
- [ ] Train Word2Vec.
- [ ] Export dense vectors.
- [ ] Buat hybrid ranking.
- [ ] Jalankan evaluation test cases.
- [ ] Export recommendation examples.
- [ ] Export model comparison summary.

### Vector DB

- [ ] Jalankan Qdrant.
- [ ] Buat collection `movies`.
- [ ] Index vector film.
- [ ] Test vector search.
- [ ] Test metadata payload.

### Backend

- [ ] Setup FastAPI.
- [ ] Endpoint `/health`.
- [ ] Endpoint `/movies/search`.
- [ ] Endpoint `/recommend/similar`.
- [ ] Endpoint `/chat`.
- [ ] Error handling judul tidak ditemukan.

### Frontend

- [ ] Setup Streamlit.
- [ ] Chat input.
- [ ] Render response.
- [ ] Render recommendation card.
- [ ] Loading state.
- [ ] Error state.

### Documentation

- [ ] README.
- [ ] Architecture doc.
- [ ] Model evaluation doc.
- [ ] Demo script.
- [ ] Screenshot aplikasi.
- [ ] Final presentation points.

## Pembagian Jika Tim 4 Orang

### Anggota 1 - Data Engineer

Fokus:

- dataset final
- validasi data
- export data processed
- data summary

### Anggota 2 - ML Engineer

Fokus:

- TF-IDF
- Word2Vec
- hybrid ranking
- evaluasi model

### Anggota 3 - Backend + Database

Fokus:

- Qdrant
- indexing vector
- FastAPI
- endpoint rekomendasi

### Anggota 4 - Frontend + Documentation

Fokus:

- Streamlit UI
- screenshot
- README
- demo script
- slide/laporan

## Pembagian Jika Tim 5 Orang

### Anggota 1 - Data Engineer

Fokus data final dan validasi.

### Anggota 2 - ML Engineer

Fokus training dan evaluasi model.

### Anggota 3 - Backend Engineer

Fokus FastAPI dan business logic.

### Anggota 4 - Frontend Engineer

Fokus chatbot UI.

### Anggota 5 - Documentation + Presentation

Fokus laporan, diagram, screenshot, dan narasi demo.

## Demo Script Singkat

Gunakan alur ini saat presentasi:

1. Jelaskan masalah:
   - user ingin rekomendasi film dengan bahasa natural.
2. Jelaskan data:
   - TMDB, sekitar 80 ribu film.
3. Jelaskan preprocessing:
   - metadata digabung menjadi `movie_document_weighted`.
4. Jelaskan model:
   - TF-IDF dan Word2Vec dilatih dari corpus film.
5. Jelaskan vector database:
   - Qdrant dipakai untuk similarity search cepat.
6. Jelaskan chatbot:
   - LLM membantu memahami pertanyaan dan menjelaskan hasil.
7. Demo:
   - ketik "rekomendasi film selain Interstellar".
8. Tunjukkan hasil:
   - list film + alasan.
9. Tutup:
   - sistem adalah content-based recommendation dengan RAG ringan.

