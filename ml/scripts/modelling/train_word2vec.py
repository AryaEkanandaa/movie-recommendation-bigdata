"""
Train Word2Vec movie vectors for Qdrant indexing.

Input:
- ml/data/processed/movies_final.csv

Outputs:
- ml/models/recommendation/word2vec_model/
- ml/data/processed/movie_vectors_word2vec.parquet
- ml/reports/modelling/word2vec_summary.csv
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from pyspark.ml.feature import RegexTokenizer, StopWordsRemover, Word2Vec
from pyspark.ml.functions import vector_to_array
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


ML_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ML_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
REPORT_DIR = ML_DIR / "reports" / "modelling"
MODEL_DIR = ML_DIR / "models" / "recommendation" / "word2vec_model"

MOVIES_FINAL_PATH = PROCESSED_DIR / "movies_final.csv"
VECTOR_OUTPUT = PROCESSED_DIR / "movie_vectors_word2vec.parquet"
SUMMARY_OUTPUT = REPORT_DIR / "word2vec_summary.csv"

VECTOR_SIZE = int(os.getenv("WORD2VEC_VECTOR_SIZE", "64"))
MIN_COUNT = int(os.getenv("WORD2VEC_MIN_COUNT", "5"))
MAX_ITER = int(os.getenv("WORD2VEC_MAX_ITER", "5"))
NUM_PARTITIONS = int(os.getenv("SPARK_NUM_PARTITIONS", "4"))


def remove_existing_path(path: Path) -> None:
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("movie-word2vec-training")
        .master(os.getenv("SPARK_MASTER", "local[*]"))
        .config("spark.sql.shuffle.partitions", str(NUM_PARTITIONS))
        .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "4g"))
        .getOrCreate()
    )


def main() -> None:
    if not MOVIES_FINAL_PATH.exists():
        raise FileNotFoundError(
            f"{MOVIES_FINAL_PATH} not found. Run finalize_datasets.py first."
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)

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
            "popularity",
            "recommendation_quality_score",
            "movie_document_weighted",
        )
        .dropna(subset=["id", "title", "movie_document_weighted"])
        .withColumn("id", F.col("id").cast("long"))
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

    word2vec = Word2Vec(
        vectorSize=VECTOR_SIZE,
        minCount=MIN_COUNT,
        maxIter=MAX_ITER,
        inputCol="filtered_tokens",
        outputCol="word2vec_features",
        seed=42,
    )

    model = word2vec.fit(prepared)
    vectors = model.transform(prepared)

    output = (
        vectors.withColumn("vector", vector_to_array("word2vec_features"))
        .select(
            "id",
            "title",
            "release_year",
            "genres_text",
            "vote_average",
            "vote_count",
            "popularity",
            "recommendation_quality_score",
            "vector",
        )
        .orderBy("id")
    )

    remove_existing_path(MODEL_DIR)
    remove_existing_path(VECTOR_OUTPUT)

    model.save(str(MODEL_DIR))
    output.write.mode("overwrite").parquet(str(VECTOR_OUTPUT))

    movie_count = output.count()
    vocab_size = len(model.getVectors().collect())
    avg_token_count = prepared.select(F.avg(F.size("filtered_tokens"))).first()[0]

    remove_existing_path(SUMMARY_OUTPUT)
    summary_rows = [
        ("movie_count", str(movie_count)),
        ("vector_size", str(VECTOR_SIZE)),
        ("min_count", str(MIN_COUNT)),
        ("max_iter", str(MAX_ITER)),
        ("vocabulary_size", str(vocab_size)),
        ("avg_filtered_token_count", f"{avg_token_count:.4f}"),
        ("vector_output", str(VECTOR_OUTPUT)),
        ("model_output", str(MODEL_DIR)),
    ]
    with SUMMARY_OUTPUT.open("w", encoding="utf-8", newline="") as file:
        file.write("metric,value\n")
        for metric, value in summary_rows:
            escaped_value = value.replace('"', '""')
            file.write(f'{metric},"{escaped_value}"\n')

    print(f"Saved Word2Vec model : {MODEL_DIR}")
    print(f"Saved movie vectors  : {VECTOR_OUTPUT}")
    print(f"Saved summary        : {SUMMARY_OUTPUT}")
    print(f"Movie vectors        : {movie_count:,}")
    print(f"Vocabulary size      : {vocab_size:,}")

    spark.stop()


if __name__ == "__main__":
    main()
