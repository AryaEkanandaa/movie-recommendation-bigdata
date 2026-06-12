# MVP Plan - LLM Chatbot Movie Recommendation

## 1. Problem Statement

Project ini bertujuan membuat aplikasi rekomendasi film berbentuk chatbot. User tidak perlu memilih filter secara manual, tetapi cukup bertanya dengan bahasa natural.

Contoh:

```text
Apa rekomendasi film selain Interstellar?
Film seperti The Dark Knight tapi lebih baru
Rekomendasi film animasi keluarga dengan rating bagus
```

Masalah utama yang diselesaikan:

- User ingin rekomendasi film yang relevan dengan konteks.
- Dataset tidak memiliki data interaksi user seperti rating personal, watch history, atau click history.
- Karena itu, pendekatan yang paling cocok adalah content-based recommendation.

## 2. MVP Definition

MVP selesai jika sistem bisa:

1. Menerima input chat dari user.
2. Mendeteksi judul film atau kriteria rekomendasi.
3. Mengambil kandidat rekomendasi dari vector database.
4. Melakukan ranking ulang dengan skor hybrid.
5. Mengembalikan 5-10 film beserta alasan rekomendasi.

Output minimal untuk setiap film:

- title
- release_year
- genres
- vote_average
- overview pendek
- reason

Contoh output:

```text
Berikut rekomendasi film selain Interstellar:

1. Arrival (2016)
   Cocok karena sama-sama sci-fi drama dengan tema komunikasi, waktu, dan emosi manusia.

2. Contact (1997)
   Cocok karena membahas eksplorasi luar angkasa dan pertanyaan besar tentang manusia.
```

## 3. Data Yang Digunakan

File utama:

```text
data/tmdb_movie_documents.csv
data/tmdb_movies_model_ready.csv
```

Kolom penting dari `tmdb_movie_documents.csv`:

- `id`
- `title`
- `original_title`
- `release_date`
- `release_year`
- `movie_era`
- `original_language`
- `genres_text`
- `director_clean`
- `top_cast_text`
- `keywords_text`
- `overview_clean`
- `tagline_clean`
- `runtime`
- `vote_average`
- `vote_count`
- `popularity`
- `budget`
- `revenue`
- `recommendation_quality_score`
- `movie_document_basic`
- `movie_document_rich`
- `movie_document_weighted`

Kolom utama untuk training:

```text
movie_document_weighted
```

Alasan:

- Sudah menggabungkan title, genre, director, cast, keywords, overview, dan tagline.
- Cocok untuk content-based recommendation.
- Bisa dipakai untuk TF-IDF dan Word2Vec.

## 4. Arsitektur Sistem

Arsitektur MVP:

```text
User
  |
  v
Frontend Chat UI
  |
  v
FastAPI Backend
  |
  +--> Intent Parser
  |
  +--> Movie Title Search
  |
  +--> Qdrant Vector Search
  |
  +--> Hybrid Re-ranking
  |
  +--> LLM Explanation
  |
  v
Chat Response
```

Komponen:

- Frontend: tempat user chat.
- Backend: mengatur proses rekomendasi.
- Qdrant: menyimpan vector film dan metadata penting.
- Model recommender: menghasilkan vector dan similarity.
- LLM: menyusun jawaban natural berdasarkan hasil retrieval.

## 5. Peran RAG Dalam Project

Project ini menggunakan RAG ringan, bukan RAG dokumen panjang.

RAG di sini berarti:

```text
Retrieve film dari database -> beri konteks ke LLM -> LLM menjawab
```

LLM tidak boleh membuat rekomendasi dari ingatan sendiri. LLM hanya menjelaskan film yang sudah diambil oleh sistem.

Manfaat:

- Mengurangi halusinasi.
- Jawaban berbasis data TMDB.
- Hasil rekomendasi bisa dikontrol dengan ranking model.

## 6. Model Training

Karena rencananya melatih model sendiri, model yang dilatih adalah model rekomendasi, bukan LLM.

### 6.1 Baseline Model - TF-IDF

Input:

```text
movie_document_weighted
```

Pipeline:

```text
Tokenizer
-> StopWordsRemover
-> CountVectorizer
-> IDF
-> TF-IDF vector
```

Similarity:

```text
Cosine Similarity
```

Kelebihan:

- Mudah dijelaskan.
- Cocok untuk metadata teks.
- Bisa dilatih dengan PySpark.
- Bagus sebagai model utama MVP.

### 6.2 Comparison Model - Word2Vec

Input:

```text
tokenized movie_document_weighted
```

Pipeline:

```text
Tokenizer
-> StopWordsRemover
-> Word2Vec
-> movie embedding
```

Kelebihan:

- Embedding dilatih dari corpus film sendiri.
- Lebih terasa sebagai model machine learning yang dilatih.
- Bisa dibandingkan dengan TF-IDF.

### 6.3 Hybrid Ranking

Setelah kandidat film didapat dari similarity search, lakukan re-ranking.

Formula awal:

```text
final_score =
0.65 * similarity_score
+ 0.10 * rating_norm
+ 0.10 * vote_count_norm
+ 0.10 * popularity_norm
+ 0.05 * quality_score
```

Normalisasi:

- `rating_norm = vote_average / 10`
- `vote_count_norm = log_vote_count / max(log_vote_count)`
- `popularity_norm = log_popularity / max(log_popularity)`
- `quality_score = recommendation_quality_score`

Formula bisa disesuaikan setelah evaluasi.

## 7. Database

### 7.1 MVP Database

Gunakan Qdrant.

Collection:

```text
movies
```

Vector:

```text
movie_vector
```

Payload:

- id
- title
- original_title
- release_year
- movie_era
- original_language
- genres_text
- director_clean
- top_cast_text
- keywords_text
- overview_clean
- tagline_clean
- runtime
- vote_average
- vote_count
- popularity
- recommendation_quality_score

### 7.2 Kenapa Qdrant

Qdrant cocok karena:

- cepat untuk vector similarity search
- support metadata payload
- support filtering
- cocok untuk dataset 80 ribuan film
- mudah dijalankan via Docker

### 7.3 Alternatif

Jika ingin lebih production-ready:

```text
PostgreSQL + pgvector
```

Jika ingin sistem paling lengkap:

```text
Qdrant untuk vector search
PostgreSQL untuk metadata, user, dan history chat
```

Untuk MVP, cukup:

```text
Qdrant only
```

## 8. Backend API

Backend disarankan menggunakan FastAPI.

Endpoint MVP:

### POST `/chat`

Input:

```json
{
  "message": "rekomendasi film selain Interstellar"
}
```

Output:

```json
{
  "answer": "Berikut rekomendasi film selain Interstellar...",
  "recommendations": [
    {
      "id": 1,
      "title": "Arrival",
      "release_year": 2016,
      "genres": "drama sci-fi",
      "vote_average": 7.6,
      "score": 0.91,
      "reason": "Sama-sama sci-fi drama dengan tema komunikasi dan waktu."
    }
  ]
}
```

### GET `/movies/search`

Fungsi:

- mencari film berdasarkan title
- membantu fuzzy matching seed movie

Contoh:

```text
/movies/search?title=interstellar
```

### GET `/recommend/similar`

Fungsi:

- rekomendasi langsung berdasarkan title

Contoh:

```text
/recommend/similar?title=Interstellar&top_k=10
```

### GET `/health`

Fungsi:

- memastikan backend dan Qdrant aktif

## 9. Query Understanding

Untuk MVP, intent parser bisa dibuat rule-based dulu.

Intent yang perlu didukung:

### 9.1 Similar Movie

Contoh:

```text
rekomendasi film selain Interstellar
film mirip Inception
seperti The Dark Knight
```

Output parser:

```json
{
  "intent": "similar_movie",
  "seed_title": "Interstellar",
  "top_k": 10
}
```

### 9.2 Genre Based

Contoh:

```text
rekomendasi film comedy romance
film horror rating bagus
```

Output parser:

```json
{
  "intent": "genre_recommendation",
  "genres": ["comedy", "romance"],
  "top_k": 10
}
```

### 9.3 Filtered Recommendation

Contoh:

```text
film sci-fi tahun 2010-an
film action setelah tahun 2020
```

Output parser:

```json
{
  "intent": "filtered_recommendation",
  "genres": ["sci-fi"],
  "year_min": 2010,
  "year_max": 2019,
  "top_k": 10
}
```

Setelah MVP stabil, intent parser bisa diganti atau dibantu LLM.

## 10. Frontend

Untuk MVP cepat:

```text
Streamlit
```

Fitur:

- input chat
- area jawaban chatbot
- daftar rekomendasi dalam card
- loading state
- error message jika judul tidak ditemukan

Untuk versi lebih rapi:

```text
React atau Next.js
```

## 11. Evaluasi

Karena dataset tidak punya interaksi user, evaluasi tidak memakai RMSE/MAE.

Evaluasi yang digunakan:

### 11.1 Genre Overlap

Mengukur kesamaan genre antara film acuan dan hasil rekomendasi.

### 11.2 Keyword Overlap

Mengukur kesamaan keyword.

### 11.3 Metadata Quality

Melihat kualitas metadata hasil rekomendasi.

### 11.4 Average Rating

Rata-rata rating film hasil rekomendasi.

### 11.5 Manual Evaluation

Gunakan test case:

- Interstellar
- Inception
- The Dark Knight
- Titanic
- Toy Story
- Parasite
- La La Land
- Spirited Away

Output evaluasi:

```text
reports/modelling/recommendation_examples.csv
reports/modelling/model_comparison_summary.csv
```

## 12. Deliverables MVP

Deliverables teknis:

- script training TF-IDF
- script training Word2Vec
- script export vector
- script indexing ke Qdrant
- FastAPI backend
- frontend chatbot sederhana
- laporan evaluasi model

Deliverables laporan:

- problem statement
- data source
- preprocessing
- model training
- database selection
- RAG architecture
- evaluation result
- screenshot aplikasi
- kesimpulan

## 13. Risiko Dan Solusi

### Risiko 1: Judul film tidak ditemukan

Solusi:

- gunakan case-insensitive search
- tambahkan fuzzy matching
- tampilkan beberapa kandidat judul

### Risiko 2: Rekomendasi terlalu populer saja

Solusi:

- turunkan bobot popularity
- naikkan bobot similarity
- beri filter genre atau year

### Risiko 3: Rekomendasi terlalu mirip secara kata, tapi tidak relevan

Solusi:

- bandingkan TF-IDF dengan Word2Vec
- tambahkan reranking dengan genre overlap
- gunakan `movie_document_weighted`

### Risiko 4: Qdrant belum bisa menyimpan sparse TF-IDF dengan nyaman

Solusi:

- untuk MVP vector DB gunakan Word2Vec dense vector
- TF-IDF tetap dipakai sebagai baseline offline
- atau ubah TF-IDF vector ke format dense jika dimensinya masih masuk akal

## 14. Prioritas Implementasi

Prioritas paling aman:

1. TF-IDF baseline di notebook/script.
2. Word2Vec dense vector untuk Qdrant.
3. Qdrant indexing.
4. Backend endpoint `/recommend/similar`.
5. Chat endpoint `/chat`.
6. Streamlit UI.
7. Evaluasi dan dokumentasi.

