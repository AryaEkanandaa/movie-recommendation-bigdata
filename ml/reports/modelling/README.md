# Modelling Reports

Folder ini memisahkan output modelling berdasarkan konteks agar mudah dibrowse.

## Struktur

- `training/`: ringkasan proses training model, misalnya Word2Vec.
- `evaluation/`: hasil evaluasi rekomendasi Word2Vec + Qdrant dengan hybrid re-ranking.
- `comparison/`: perbandingan CountVectorizer, TF-IDF, dan Word2Vec + Qdrant.

## File Penting

- `training/word2vec_summary.csv`: jumlah film, vector size, vocabulary size, dan lokasi output model/vector.
- `evaluation/recommendation_examples.csv`: contoh rekomendasi per query.
- `evaluation/model_evaluation_summary.csv`: ringkasan evaluasi per query dan overall.
- `comparison/model_comparison_examples.csv`: contoh rekomendasi dari tiap model pembanding.
- `comparison/model_comparison_summary.csv`: ringkasan perbandingan model.
