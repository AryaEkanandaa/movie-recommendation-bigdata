"""
Compare CountVectorizer, TF-IDF, and Word2Vec+Qdrant recommendations.

Outputs:
- ml/reports/modelling/comparison/model_comparison_examples.csv
- ml/reports/modelling/comparison/model_comparison_summary.csv
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pandas as pd
from pyspark.ml.feature import CountVectorizer, IDF, RegexTokenizer, StopWordsRemover
from pyspark.ml.linalg import Vector
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T


ML_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ML_DIR / "data" / "processed"
FINAL_DIR = PROCESSED_DIR / "final"
REPORT_DIR = ML_DIR / "reports" / "modelling"
EVALUATION_REPORT_DIR = REPORT_DIR / "evaluation"
COMPARISON_REPORT_DIR = REPORT_DIR / "comparison"

MOVIES_FINAL_PATH = FINAL_DIR / "movies_final.csv"
WORD2VEC_EXAMPLES_PATH = EVALUATION_REPORT_DIR / "recommendation_examples.csv"

MODEL_COMPARISON_EXAMPLES_OUTPUT = (
    COMPARISON_REPORT_DIR / "model_comparison_examples.csv"
)
MODEL_COMPARISON_SUMMARY_OUTPUT = (
    COMPARISON_REPORT_DIR / "model_comparison_summary.csv"
)

TEST_QUERIES = [
    "Interstellar",
    "Inception",
    "The Dark Knight",
    "Titanic",
    "Toy Story",
    "Avatar",
    "Parasite",
    "La La Land",
    "Spirited Away",
]

NUM_PARTITIONS = int(os.getenv("SPARK_NUM_PARTITIONS", "4"))
VOCAB_SIZE = int(os.getenv("COMPARISON_VOCAB_SIZE", "20000"))
MIN_DF = float(os.getenv("COMPARISON_MIN_DF", "5"))


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("movie-model-comparison")
        .master(os.getenv("SPARK_MASTER", "local[*]"))
        .config("spark.sql.shuffle.partitions", str(NUM_PARTITIONS))
        .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "4g"))
        .getOrCreate()
    )


def cosine_similarity(v1: Vector, v2: Vector) -> float:
    norm = float(v1.norm(2) * v2.norm(2))
    if norm == 0.0:
        return 0.0
    return float(v1.dot(v2) / norm)


def normalize_genres(genres: Any) -> set[str]:
    if pd.isna(genres):
        return set()
    return {part.strip().lower() for part in str(genres).split() if part.strip()}


def genre_overlap(source_genres: Any, recommended_genres: Any) -> float:
    source = normalize_genres(source_genres)
    recommended = normalize_genres(recommended_genres)
    if not source or not recommended:
        return 0.0
    return len(source & recommended) / len(source | recommended)


def find_source_row(features_df, query: str):
    exact = features_df.filter(F.lower(F.col("title")) == query.lower()).orderBy(
        "title", "release_year"
    )
    exact_rows = exact.limit(1).collect()
    if exact_rows:
        return exact_rows[0]

    fuzzy = features_df.filter(F.lower(F.col("title")).contains(query.lower())).orderBy(
        "title", "release_year"
    )
    fuzzy_rows = fuzzy.limit(1).collect()
    if fuzzy_rows:
        return fuzzy_rows[0]

    raise ValueError(f"No movie matched query: {query}")


def recommend_with_feature_column(
    features_df,
    query: str,
    model_name: str,
    feature_col: str,
    top_k: int,
) -> list[dict[str, Any]]:
    source = find_source_row(features_df, query)
    source_id = int(source["id"])
    source_vector = source[feature_col]
    source_genres = source["genres_text"]

    cosine_udf = F.udf(
        lambda vector: cosine_similarity(vector, source_vector), T.DoubleType()
    )

    result_rows = (
        features_df.filter(F.col("id") != source_id)
        .withColumn("similarity_score", cosine_udf(F.col(feature_col)))
        .orderBy(F.desc("similarity_score"), F.desc("vote_count"))
        .select(
            "id",
            "title",
            "release_year",
            "genres_text",
            "vote_average",
            "vote_count",
            "similarity_score",
        )
        .limit(top_k)
        .collect()
    )

    rows = []
    for rank, row in enumerate(result_rows, start=1):
        rows.append(
            {
                "model": model_name,
                "query": source["title"],
                "source_id": source_id,
                "source_title": source["title"],
                "source_release_year": source["release_year"],
                "source_genres": source_genres,
                "rank": rank,
                "recommended_id": int(row["id"]),
                "recommended_title": row["title"],
                "recommended_release_year": row["release_year"],
                "recommended_genres": row["genres_text"],
                "vote_average": row["vote_average"],
                "vote_count": row["vote_count"],
                "score": row["similarity_score"],
                "genre_overlap": genre_overlap(source_genres, row["genres_text"]),
            }
        )

    return rows


def load_word2vec_examples() -> pd.DataFrame:
    if not WORD2VEC_EXAMPLES_PATH.exists():
        return pd.DataFrame()

    examples = pd.read_csv(WORD2VEC_EXAMPLES_PATH)
    rows = pd.DataFrame(
        {
            "model": "Word2Vec + Qdrant",
            "query": examples["query"],
            "source_id": examples["source_id"],
            "source_title": examples["source_title"],
            "source_release_year": examples["source_release_year"],
            "source_genres": examples["source_genres"],
            "rank": examples["rank"],
            "recommended_id": examples["recommended_id"],
            "recommended_title": examples["recommended_title"],
            "recommended_release_year": examples["recommended_release_year"],
            "recommended_genres": examples["recommended_genres"],
            "vote_average": examples["vote_average"],
            "vote_count": examples["vote_count"],
            "score": examples["similarity_score"],
            "genre_overlap": examples["genre_overlap"],
        }
    )
    return rows


def build_summary(examples: pd.DataFrame) -> pd.DataFrame:
    summary = (
        examples.groupby("model", as_index=False)
        .agg(
            recommendation_count=("recommended_id", "count"),
            avg_score=("score", "mean"),
            avg_genre_overlap=("genre_overlap", "mean"),
            avg_vote_average=("vote_average", "mean"),
            avg_vote_count=("vote_count", "mean"),
        )
        .round(
            {
                "avg_score": 4,
                "avg_genre_overlap": 4,
                "avg_vote_average": 4,
                "avg_vote_count": 4,
            }
        )
        .sort_values(["avg_genre_overlap", "avg_score"], ascending=False)
    )
    return summary


def main() -> None:
    if not MOVIES_FINAL_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {MOVIES_FINAL_PATH}")

    COMPARISON_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    movies = (
        spark.read.option("header", True)
        .option("multiLine", True)
        .option("escape", '"')
        .csv(str(MOVIES_FINAL_PATH))
        .select(
            "id",
            "title",
            "release_year",
            "genres_text",
            "vote_average",
            "vote_count",
            "movie_document_weighted",
        )
        .dropna(subset=["id", "title", "movie_document_weighted"])
        .withColumn("id", F.col("id").cast("long"))
        .withColumn("release_year", F.col("release_year").cast("int"))
        .withColumn("vote_average", F.col("vote_average").cast("double"))
        .withColumn("vote_count", F.col("vote_count").cast("double"))
        .withColumn(
            "movie_document_weighted",
            F.trim(F.col("movie_document_weighted").cast("string")),
        )
        .filter(F.col("movie_document_weighted") != "")
        .repartition(NUM_PARTITIONS)
    )

    tokenizer = RegexTokenizer(
        inputCol="movie_document_weighted",
        outputCol="tokens",
        pattern="\\W+",
        gaps=True,
        minTokenLength=2,
        toLowercase=True,
    )
    tokenized = tokenizer.transform(movies)

    remover = StopWordsRemover(inputCol="tokens", outputCol="filtered_tokens")
    prepared = remover.transform(tokenized).filter(F.size("filtered_tokens") > 0)

    count_vectorizer = CountVectorizer(
        inputCol="filtered_tokens",
        outputCol="count_features",
        vocabSize=VOCAB_SIZE,
        minDF=MIN_DF,
    )
    count_model = count_vectorizer.fit(prepared)
    count_features = count_model.transform(prepared).cache()

    idf = IDF(inputCol="count_features", outputCol="tfidf_features")
    idf_model = idf.fit(count_features)
    all_features = idf_model.transform(count_features).cache()
    all_features.count()

    top_k = int(os.getenv("EVALUATION_TOP_K", "10"))
    all_rows: list[dict[str, Any]] = []

    for query in TEST_QUERIES:
        all_rows.extend(
            recommend_with_feature_column(
                all_features,
                query=query,
                model_name="CountVectorizer + Cosine",
                feature_col="count_features",
                top_k=top_k,
            )
        )
        all_rows.extend(
            recommend_with_feature_column(
                all_features,
                query=query,
                model_name="TF-IDF + Cosine",
                feature_col="tfidf_features",
                top_k=top_k,
            )
        )
        print(f"Compared CountVectorizer and TF-IDF for query: {query}")

    spark_examples = pd.DataFrame(all_rows)
    word2vec_examples = load_word2vec_examples()
    examples = pd.concat([spark_examples, word2vec_examples], ignore_index=True)
    summary = build_summary(examples)

    examples.to_csv(MODEL_COMPARISON_EXAMPLES_OUTPUT, index=False)
    summary.to_csv(MODEL_COMPARISON_SUMMARY_OUTPUT, index=False)

    print(f"Saved examples : {MODEL_COMPARISON_EXAMPLES_OUTPUT}")
    print(f"Saved summary  : {MODEL_COMPARISON_SUMMARY_OUTPUT}")
    print(f"Total rows     : {len(examples):,}")

    spark.stop()


if __name__ == "__main__":
    main()
