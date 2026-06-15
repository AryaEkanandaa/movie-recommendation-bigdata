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
ml/data/processed/movie_vectors_word2vec.parquet
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
- rata-rata genre overlap,
- rata-rata vote average,
- rata-rata vote count.

Script evaluasi:

```bash
docker compose run --rm ml python ml/scripts/modelling/evaluate_recommendations.py
```

Output:

```text
ml/reports/modelling/recommendation_examples.csv
ml/reports/modelling/model_evaluation_summary.csv
```

## Hasil Evaluasi Saat Ini

Evaluasi terakhir menghasilkan:

```text
total recommendations     : 90
overall avg similarity    : 0.8992
overall avg genre overlap : 0.5740
overall avg vote average  : 6.5181
overall avg vote count    : 4079.2
```

Ringkasan per query:

| Query | Avg Similarity | Avg Genre Overlap | Avg Vote Average |
| --- | ---: | ---: | ---: |
| Avatar | 0.8991 | 0.6833 | 6.1508 |
| Inception | 0.8541 | 0.5300 | 6.5039 |
| Interstellar | 0.9219 | 0.6283 | 7.1414 |
| La La Land | 0.8907 | 0.4917 | 6.0450 |
| Parasite | 0.8987 | 0.6800 | 5.0176 |
| Spirited Away | 0.9540 | 0.5219 | 7.4449 |
| The Dark Knight | 0.9156 | 0.5067 | 6.9597 |
| Titanic | 0.8513 | 0.3843 | 6.4005 |
| Toy Story | 0.9079 | 0.7400 | 6.9988 |

Contoh hasil untuk `Interstellar`:

| Rank | Recommendation | Year | Similarity |
| ---: | --- | ---: | ---: |
| 1 | The Martian | 2015 | 0.9460 |
| 2 | Project Hail Mary | 2026 | 0.9354 |
| 3 | Armageddon | 1998 | 0.9261 |
| 4 | Star Trek | 2009 | 0.9226 |
| 5 | Mars Attacks! | 1996 | 0.9220 |
| 6 | Arrival | 2016 | 0.9186 |

Catatan evaluasi:

- Hasil untuk `Interstellar`, `The Dark Knight`, dan `Toy Story` cukup relevan secara genre/konteks.
- Beberapa query masih bisa menghasilkan film yang kurang populer atau kurang sesuai secara kualitas.
- Karena itu tahap berikutnya adalah menambahkan hybrid re-ranking agar similarity digabung dengan rating, vote count, popularity, dan quality score.

## Jawaban Singkat Untuk Presentasi

Model yang digunakan adalah content-based recommendation dengan PySpark ML Word2Vec. Input model adalah `movie_document_weighted`, yaitu gabungan metadata film seperti genre, director, cast, keywords, overview, dan tagline. Word2Vec mengubah setiap film menjadi vector 64 dimensi. Vector tersebut disimpan ke Qdrant, lalu rekomendasi dihasilkan dengan cosine similarity search.
