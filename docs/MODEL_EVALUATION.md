# Model Evaluation

Dokumen ini menjelaskan model rekomendasi yang digunakan, alasan pemilihan model, dan cara evaluasinya.

## Pendekatan

Project ini menggunakan **content-based recommendation**.

Alasannya: dataset tidak memiliki data interaksi user seperti `user_id`, histori menonton, rating personal, atau click history. Karena itu, rekomendasi dibuat berdasarkan kemiripan konten/metadata film.

## Model Runtime MVP

Model yang digunakan untuk MVP runtime:

```text
PySpark ML Word2Vec + Qdrant
```

Input model:

```text
movie_document_weighted
```

Kolom tersebut adalah gabungan metadata film, seperti:

- title
- genres
- director
- cast
- keywords
- overview
- tagline

Output model:

```text
embedding/vector film 64 dimensi
```

Vector film disimpan di:

```text
ml/data/processed/vectors/movie_vectors_word2vec.parquet
```

Model Word2Vec disimpan sebagai folder PySpark ML:

```text
ml/models/recommendation/word2vec_model/
```

Model tidak disimpan sebagai `.pkl` karena `.pkl` umum dipakai pada scikit-learn, sedangkan project ini menggunakan PySpark ML.

## Vector Database

Vector film di-index ke Qdrant collection:

```text
movies
```

Distance yang digunakan:

```text
Cosine
```

Saat user meminta film mirip, sistem:

1. mencari film acuan,
2. mengambil vector film acuan,
3. mencari vector film paling mirip di Qdrant,
4. mengembalikan top recommendation.

## Peran Model Lama Di Notebook

Notebook modelling lama memuat:

- CountVectorizer
- TF-IDF + Cosine Similarity
- K-Means clustering
- draft hybrid ranking

Perannya:

- **CountVectorizer**: baseline sederhana berbasis frekuensi kata.
- **TF-IDF**: baseline teks yang lebih kuat untuk pembanding.
- **K-Means**: analisis segmentasi film, bukan model rekomendasi utama.
- **Word2Vec**: model dense vector untuk Qdrant runtime.

Untuk MVP aplikasi, runtime menggunakan Word2Vec + Qdrant karena Qdrant cocok untuk dense vector yang ringan dan cepat dicari.

## Evaluasi

Evaluasi dilakukan dengan beberapa query film:

- Interstellar
- Inception
- The Dark Knight
- Titanic
- Toy Story
- Avatar
- Parasite
- La La Land
- Spirited Away

Metric sederhana:

- jumlah rekomendasi yang berhasil dikembalikan,
- rata-rata similarity score,
- rata-rata hybrid score,
- rata-rata genre overlap,
- rata-rata vote average,
- rata-rata vote count.

Script evaluasi:

```bash
docker compose run --rm ml python ml/scripts/modelling/evaluate_recommendations.py
```

Output:

```text
ml/reports/modelling/evaluation/recommendation_examples.csv
ml/reports/modelling/evaluation/model_evaluation_summary.csv
```

Untuk membandingkan CountVectorizer, TF-IDF, dan Word2Vec + Qdrant:

```bash
docker compose run --rm ml python ml/scripts/modelling/compare_text_models.py
```

Output:

```text
ml/reports/modelling/comparison/model_comparison_examples.csv
ml/reports/modelling/comparison/model_comparison_summary.csv
```

## Hybrid Re-Ranking

Qdrant mengembalikan kandidat berdasarkan similarity vector. Setelah itu kandidat diurutkan ulang dengan hybrid score:

```text
hybrid_score =
0.70 * similarity_score
+ 0.10 * rating_norm
+ 0.08 * vote_count_norm
+ 0.07 * popularity_norm
+ 0.05 * quality_norm
```

Alasannya: similarity saja belum cukup. Film yang mirip tetapi kurang kuat dari sisi rating, vote count, popularity, atau metadata quality bisa turun, sedangkan film yang mirip dan kualitasnya lebih baik bisa naik.

## Hasil Evaluasi Saat Ini

Evaluasi terakhir menghasilkan:

```text
total recommendations     : 90
overall avg similarity    : 0.8921
overall avg hybrid score  : 0.7613
overall avg genre overlap : 0.5671
overall avg vote average  : 7.1796
overall avg vote count    : 7034.0
```

Ringkasan per query:

| Query | Avg Similarity | Avg Hybrid | Avg Genre Overlap | Avg Vote Average |
| --- | ---: | ---: | ---: | ---: |
| Avatar | 0.8927 | 0.7460 | 0.5333 | 7.0441 |
| Inception | 0.8464 | 0.7378 | 0.5467 | 7.0102 |
| Interstellar | 0.9173 | 0.7917 | 0.6183 | 7.3754 |
| La La Land | 0.8780 | 0.7511 | 0.5583 | 7.3764 |
| Parasite | 0.8937 | 0.7331 | 0.6250 | 5.7559 |
| Spirited Away | 0.9513 | 0.8010 | 0.5333 | 7.8912 |
| The Dark Knight | 0.9097 | 0.7858 | 0.4933 | 7.4161 |
| Titanic | 0.8427 | 0.7231 | 0.4060 | 7.0826 |
| Toy Story | 0.8973 | 0.7824 | 0.7900 | 7.6644 |

Contoh hasil untuk `Interstellar`:

| Rank | Recommendation | Year | Similarity | Hybrid |
| ---: | --- | ---: | ---: | ---: |
| 1 | The Martian | 2015 | 0.9460 | 0.8329 |
| 2 | Project Hail Mary | 2026 | 0.9354 | 0.8171 |
| 3 | Arrival | 2016 | 0.9186 | 0.8093 |
| 4 | Star Trek | 2009 | 0.9226 | 0.7917 |
| 5 | Passengers | 2016 | 0.9103 | 0.7857 |
| 6 | Armageddon | 1998 | 0.9261 | 0.7845 |

## Perbandingan Model

Perbandingan pada 9 query x 10 rekomendasi:

| Model | Recommendation Count | Avg Score | Avg Genre Overlap | Avg Vote Average | Avg Vote Count |
| --- | ---: | ---: | ---: | ---: | ---: |
| CountVectorizer + Cosine | 90 | 0.2951 | 0.5928 | 6.4357 | 2137.5 |
| Word2Vec + Qdrant | 90 | 0.8921 | 0.5671 | 7.1796 | 7034.0 |
| TF-IDF + Cosine | 90 | 0.2566 | 0.2589 | 6.5080 | 2003.7 |

Interpretasi:

- CountVectorizer memiliki genre overlap rata-rata sedikit lebih tinggi, tetapi rekomendasinya lebih sederhana karena hanya berbasis frekuensi kata.
- Word2Vec + Qdrant memberi rekomendasi dengan rating dan vote count rata-rata lebih tinggi, serta cocok untuk runtime aplikasi karena vector-nya dense dan cepat dicari.
- TF-IDF tetap berguna sebagai baseline teks, tetapi pada konfigurasi evaluasi ini genre overlap-nya lebih rendah.
- Untuk MVP, Word2Vec + Qdrant dipilih sebagai runtime karena paling cocok untuk vector database dan deployment backend.

Catatan evaluasi:

- Hasil untuk `Interstellar`, `The Dark Knight`, dan `Toy Story` cukup relevan secara genre/konteks.
- Beberapa query masih bisa menghasilkan film yang kurang sesuai secara semantik, sehingga intent parsing dan filter metadata tetap diperlukan di backend.
- Hybrid re-ranking memperbaiki kualitas rata-rata rekomendasi dari sisi rating dan vote count.

## Jawaban Singkat Untuk Presentasi

Model yang digunakan adalah content-based recommendation dengan PySpark ML Word2Vec. Input model adalah `movie_document_weighted`, yaitu gabungan metadata film seperti genre, director, cast, keywords, overview, dan tagline. Word2Vec mengubah setiap film menjadi vector 64 dimensi. Vector tersebut disimpan ke Qdrant, lalu rekomendasi dihasilkan dengan cosine similarity search.
