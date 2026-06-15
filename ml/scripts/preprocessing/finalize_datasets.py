"""
Finalize movie datasets for modelling and application payloads.

Inputs:
- ml/data/curated/tmdb_movie_documents.csv
- ml/data/curated/tmdb_movies_model_ready.csv

Outputs:
- ml/data/processed/final/movies_final.csv
- ml/data/processed/final/movies_payload.csv
- ml/reports/data/data_summary.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ML_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ML_DIR / "data"
CURATED_DIR = DATA_DIR / "curated"
REPORT_DIR = ML_DIR / "reports" / "data"
FINAL_DIR = DATA_DIR / "processed" / "final"

MOVIE_DOCUMENTS_PATH = CURATED_DIR / "tmdb_movie_documents.csv"
MODEL_READY_PATH = CURATED_DIR / "tmdb_movies_model_ready.csv"

MOVIES_FINAL_OUTPUT = FINAL_DIR / "movies_final.csv"
MOVIES_PAYLOAD_OUTPUT = FINAL_DIR / "movies_payload.csv"
DATA_SUMMARY_OUTPUT = REPORT_DIR / "data_summary.csv"

REQUIRED_DOCUMENT_COLUMNS = [
    "id",
    "title",
    "movie_document_weighted",
    "genres_text",
    "release_year",
    "runtime",
    "vote_average",
    "vote_count",
    "popularity",
    "recommendation_quality_score",
]

NUMERIC_COLUMNS = [
    "id",
    "release_year",
    "runtime",
    "vote_average",
    "vote_count",
    "popularity",
    "budget",
    "revenue",
    "recommendation_quality_score",
]

PAYLOAD_COLUMNS = [
    "id",
    "title",
    "original_title",
    "release_date",
    "release_year",
    "movie_era",
    "original_language",
    "genres_text",
    "director_clean",
    "top_cast_text",
    "keywords_text",
    "overview_clean",
    "tagline_clean",
    "runtime",
    "vote_average",
    "vote_count",
    "popularity",
    "budget",
    "revenue",
    "recommendation_quality_score",
]


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")


def require_columns(df: pd.DataFrame, columns: list[str], source_name: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{source_name} is missing required columns: {missing}")


def clean_text_column(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def load_and_validate_documents() -> pd.DataFrame:
    require_file(MOVIE_DOCUMENTS_PATH)

    movies = pd.read_csv(MOVIE_DOCUMENTS_PATH)
    require_columns(movies, REQUIRED_DOCUMENT_COLUMNS, MOVIE_DOCUMENTS_PATH.name)

    rows_before = len(movies)

    for column in ["title", "movie_document_weighted", "genres_text"]:
        movies[column] = clean_text_column(movies[column])

    for column in NUMERIC_COLUMNS:
        if column in movies.columns:
            movies[column] = pd.to_numeric(movies[column], errors="coerce")

    movies = movies.dropna(subset=["id"])
    movies["id"] = movies["id"].astype("int64")

    movies = movies[
        (movies["title"] != "")
        & (movies["movie_document_weighted"] != "")
        & (movies["genres_text"] != "")
    ].copy()

    movies = movies.sort_values(
        ["recommendation_quality_score", "vote_count", "popularity"],
        ascending=False,
        na_position="last",
    )
    movies = movies.drop_duplicates(subset=["id"], keep="first")
    movies = movies.sort_values("id").reset_index(drop=True)

    movies.attrs["rows_before"] = rows_before
    return movies


def load_optional_model_ready_columns() -> pd.DataFrame:
    if not MODEL_READY_PATH.exists():
        return pd.DataFrame(columns=["id"])

    optional_columns = [
        "id",
        "poster_path",
        "backdrop_path",
        "status",
        "imdb_id",
        "homepage",
        "genres_final_list_str",
        "production_companies_text",
        "production_countries_text",
        "spoken_languages_text",
        "writers_text",
    ]

    header = pd.read_csv(MODEL_READY_PATH, nrows=0).columns
    existing_columns = [column for column in optional_columns if column in header]
    model_ready = pd.read_csv(MODEL_READY_PATH, usecols=existing_columns)

    if "id" in model_ready.columns:
        model_ready["id"] = pd.to_numeric(model_ready["id"], errors="coerce")
        model_ready = model_ready.dropna(subset=["id"])
        model_ready["id"] = model_ready["id"].astype("int64")
        model_ready = model_ready.drop_duplicates(subset=["id"], keep="first")

    return model_ready


def build_data_summary(movies: pd.DataFrame) -> pd.DataFrame:
    rows_before = int(movies.attrs.get("rows_before", len(movies)))

    summary = {
        "rows_input": rows_before,
        "rows_final": len(movies),
        "rows_removed": rows_before - len(movies),
        "unique_movies": movies["id"].nunique(),
        "duplicate_ids_final": int(movies["id"].duplicated().sum()),
        "empty_title_final": int((movies["title"] == "").sum()),
        "empty_movie_document_weighted_final": int(
            (movies["movie_document_weighted"] == "").sum()
        ),
        "empty_genres_text_final": int((movies["genres_text"] == "").sum()),
        "avg_vote_average": round(movies["vote_average"].mean(), 4),
        "avg_vote_count": round(movies["vote_count"].mean(), 4),
        "avg_popularity": round(movies["popularity"].mean(), 4),
        "avg_recommendation_quality_score": round(
            movies["recommendation_quality_score"].mean(), 4
        ),
        "min_release_year": int(movies["release_year"].min()),
        "max_release_year": int(movies["release_year"].max()),
    }

    return pd.DataFrame(
        [{"metric": metric, "value": value} for metric, value in summary.items()]
    )


def main() -> None:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    movies = load_and_validate_documents()
    model_ready = load_optional_model_ready_columns()

    if not model_ready.empty:
        extra_columns = [column for column in model_ready.columns if column != "id"]
        movies_final = movies.merge(model_ready, on="id", how="left")
        print(f"Added optional payload columns: {extra_columns}")
    else:
        movies_final = movies
        print("No optional model-ready metadata found.")

    payload_columns = [
        column for column in PAYLOAD_COLUMNS if column in movies_final.columns
    ]
    optional_payload_columns = [
        column
        for column in [
            "poster_path",
            "backdrop_path",
            "status",
            "imdb_id",
            "homepage",
            "genres_final_list_str",
            "production_companies_text",
            "production_countries_text",
            "spoken_languages_text",
            "writers_text",
        ]
        if column in movies_final.columns
    ]

    movies_payload = movies_final[payload_columns + optional_payload_columns].copy()
    data_summary = build_data_summary(movies)

    movies_final.to_csv(MOVIES_FINAL_OUTPUT, index=False)
    movies_payload.to_csv(MOVIES_PAYLOAD_OUTPUT, index=False)
    data_summary.to_csv(DATA_SUMMARY_OUTPUT, index=False)

    print(f"Saved final dataset : {MOVIES_FINAL_OUTPUT}")
    print(f"Saved payload       : {MOVIES_PAYLOAD_OUTPUT}")
    print(f"Saved data summary  : {DATA_SUMMARY_OUTPUT}")
    print(f"Final rows          : {len(movies_final):,}")


if __name__ == "__main__":
    main()
