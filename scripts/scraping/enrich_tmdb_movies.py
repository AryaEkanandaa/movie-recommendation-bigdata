"""
TMDB Movie Enrichment Script (NO REVIEWS)
=========================================

Input  : data/raw/tmdb/tmdb_movies_final_vote10.csv
Output : data/raw/tmdb/tmdb_movies_final_vote10_enriched.csv
Batch  : data/raw/tmdb/enrich_batches/enrich_batch_*.csv
Failure: data/raw/tmdb/failures/enrich_failures.csv

Fitur:
- Resume aman: movie yang sudah ada di enrich_batches tidak diambil ulang.
- Tidak mengambil reviews.
- Mengambil detail movie + credits + keywords.
- Simpan per batch agar kalau berhenti bisa dilanjutkan.
- Saat selesai / Ctrl+C, script mencoba membuat final CSV dari batch yang sudah ada.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# =====================
# PATH CONFIG
# =====================
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw" / "tmdb"
ENRICH_BATCH_DIR = RAW_DIR / "enrich_batches"
FAILURE_DIR = RAW_DIR / "failures"

ENRICH_BATCH_DIR.mkdir(parents=True, exist_ok=True)
FAILURE_DIR.mkdir(parents=True, exist_ok=True)

INPUT_CSV = Path(os.getenv("BASE_MOVIES_CSV", RAW_DIR / "tmdb_movies_final_vote10.csv"))
ENRICH_OUTPUT_CSV = Path(
    os.getenv("ENRICH_OUTPUT_CSV", RAW_DIR / "tmdb_movies_enrichment.csv")
)
FINAL_OUTPUT_CSV = Path(
    os.getenv("FINAL_OUTPUT_CSV", RAW_DIR / "tmdb_movies_final_enriched.csv")
)
FAILURES_CSV = Path(os.getenv("ENRICH_FAILURES_CSV", FAILURE_DIR / "enrich_failures.csv"))

# =====================
# API CONFIG
# =====================
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN", "").strip()
REQUEST_SLEEP_SECONDS = float(os.getenv("REQUEST_SLEEP_SECONDS", "0.25"))
ENRICH_BATCH_SIZE = int(os.getenv("ENRICH_BATCH_SIZE", "500"))

# 0 berarti enrich semua data input.
MAX_ENRICH_ROWS = int(os.getenv("MAX_ENRICH_ROWS", "0"))

TMDB_API_BASE = "https://api.themoviedb.org/3"

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
}

# =====================
# HELPER FUNCTIONS
# =====================

def ensure_token() -> None:
    if not TMDB_BEARER_TOKEN:
        raise RuntimeError(
            "TMDB_BEARER_TOKEN belum terbaca. Isi dulu file .env di root project."
        )


def safe_join(items: Iterable[Any], sep: str = " | ") -> str:
    values: List[str] = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            values.append(text)
    return sep.join(values)


def names_from_list(items: Optional[List[Dict[str, Any]]], limit: Optional[int] = None) -> str:
    if not items:
        return ""
    names = [x.get("name") for x in items if isinstance(x, dict)]
    if limit is not None:
        names = names[:limit]
    return safe_join(names)


def fetch_movie_detail(session: requests.Session, movie_id: int, max_retries: int = 5) -> Dict[str, Any]:
    url = f"{TMDB_API_BASE}/movie/{movie_id}"
    params = {
        # Sengaja tanpa reviews.
        "append_to_response": "credits,keywords",
        "language": "en-US",
    }

    for attempt in range(max_retries):
        response = session.get(url, headers=HEADERS, params=params, timeout=30)

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "2"))
            time.sleep(retry_after + 1)
            continue

        if response.status_code in {500, 502, 503, 504}:
            time.sleep(2 * (attempt + 1))
            continue

        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")

    raise RuntimeError(f"Gagal request movie_id={movie_id} setelah {max_retries} percobaan")


def parse_movie_detail(data: Dict[str, Any]) -> Dict[str, Any]:
    credits = data.get("credits") or {}
    crew = credits.get("crew") or []
    cast = credits.get("cast") or []

    directors = [p.get("name") for p in crew if p.get("job") == "Director"]
    writers = [
        p.get("name")
        for p in crew
        if p.get("job") in {"Writer", "Screenplay", "Story", "Novel", "Characters"}
    ]

    keywords_obj = data.get("keywords") or {}
    keywords_list = keywords_obj.get("keywords") or keywords_obj.get("results") or []

    return {
        "id": data.get("id"),
        "runtime": data.get("runtime"),
        "status": data.get("status"),
        "tagline": data.get("tagline"),
        "budget": data.get("budget"),
        "revenue": data.get("revenue"),
        "imdb_id": data.get("imdb_id"),
        "homepage": data.get("homepage"),
        "genres_detail": names_from_list(data.get("genres") or []),
        "production_companies": names_from_list(data.get("production_companies") or []),
        "production_countries": names_from_list(data.get("production_countries") or []),
        "spoken_languages": names_from_list(data.get("spoken_languages") or []),
        "director": safe_join(directors),
        "writers": safe_join(writers),
        "top_cast": names_from_list(cast, limit=10),
        "keywords": names_from_list(keywords_list),
        "enriched_at": datetime.now().isoformat(timespec="seconds"),
    }


def read_nonempty_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return pd.read_csv(path)
    except Exception as exc:
        print(f"Gagal baca {path.name}: {exc}")
        return None


def load_existing_enriched_ids() -> Set[int]:
    ids: Set[int] = set()
    for path in ENRICH_BATCH_DIR.glob("enrich_batch_*.csv"):
        df = read_nonempty_csv(path)
        if df is None or "id" not in df.columns:
            continue
        ids.update(df["id"].dropna().astype(int).tolist())
    return ids


def append_failures(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    failure_df = pd.DataFrame(rows)
    if FAILURES_CSV.exists() and FAILURES_CSV.stat().st_size > 0:
        old = pd.read_csv(FAILURES_CSV)
        failure_df = pd.concat([old, failure_df], ignore_index=True)
    failure_df.to_csv(FAILURES_CSV, index=False)


def build_final_output(base_df: pd.DataFrame) -> None:
    enrich_frames: List[pd.DataFrame] = []
    for path in sorted(ENRICH_BATCH_DIR.glob("enrich_batch_*.csv")):
        df = read_nonempty_csv(path)
        if df is not None and not df.empty:
            enrich_frames.append(df)

    if not enrich_frames:
        print("Belum ada batch enrichment yang bisa digabung.")
        return

    enrich_df = pd.concat(enrich_frames, ignore_index=True)
    enrich_df = enrich_df.drop_duplicates(subset=["id"], keep="last").reset_index(drop=True)
    enrich_df.to_csv(ENRICH_OUTPUT_CSV, index=False)

    final_df = base_df.merge(enrich_df, on="id", how="left", suffixes=("", "_enrich"))
    final_df.to_csv(FINAL_OUTPUT_CSV, index=False)

    print("\n=== FINAL OUTPUT ===")
    print(f"Base rows       : {len(base_df):,}")
    print(f"Enriched rows   : {len(enrich_df):,}")
    print(f"Final rows      : {len(final_df):,}")
    print(f"Saved enrichment: {ENRICH_OUTPUT_CSV}")
    print(f"Saved final     : {FINAL_OUTPUT_CSV}")


def main() -> None:
    ensure_token()

    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Input CSV tidak ditemukan: {INPUT_CSV}\n"
            "Pastikan file tmdb_movies_final_vote10.csv ada di data/raw/tmdb/."
        )

    base_df = pd.read_csv(INPUT_CSV)
    if "id" not in base_df.columns:
        raise ValueError("Input CSV wajib punya kolom 'id'.")

    base_df = base_df.drop_duplicates(subset=["id"]).reset_index(drop=True)

    if MAX_ENRICH_ROWS > 0:
        base_df = base_df.head(MAX_ENRICH_ROWS).copy()

    existing_ids = load_existing_enriched_ids()
    all_ids = base_df["id"].dropna().astype(int).tolist()
    remaining_ids = [movie_id for movie_id in all_ids if movie_id not in existing_ids]

    print("=== TMDB ENRICHMENT NO REVIEWS ===")
    print(f"Input CSV          : {INPUT_CSV}")
    print(f"Base rows          : {len(base_df):,}")
    print(f"Already enriched   : {len(existing_ids):,}")
    print(f"Remaining          : {len(remaining_ids):,}")
    print(f"Batch size         : {ENRICH_BATCH_SIZE:,}")
    print(f"Output batch dir   : {ENRICH_BATCH_DIR}")
    print("Reviews            : DISABLED")

    session = requests.Session()
    current_batch: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    batch_start_index = len(existing_ids)

    try:
        for idx, movie_id in enumerate(tqdm(remaining_ids, desc="Enriching movies"), start=1):
            try:
                data = fetch_movie_detail(session, movie_id)
                current_batch.append(parse_movie_detail(data))
            except Exception as exc:
                failures.append(
                    {
                        "id": movie_id,
                        "error": str(exc),
                        "failed_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )

            time.sleep(REQUEST_SLEEP_SECONDS)

            if len(current_batch) >= ENRICH_BATCH_SIZE:
                start_no = batch_start_index + idx - len(current_batch) + 1
                end_no = batch_start_index + idx
                batch_path = ENRICH_BATCH_DIR / f"enrich_batch_{start_no:06d}_{end_no:06d}.csv"
                pd.DataFrame(current_batch).to_csv(batch_path, index=False)
                append_failures(failures)
                print(f"Saved batch: {batch_path.name} | rows: {len(current_batch)}")
                current_batch = []
                failures = []

        if current_batch:
            start_no = batch_start_index + len(remaining_ids) - len(current_batch) + 1
            end_no = batch_start_index + len(remaining_ids)
            batch_path = ENRICH_BATCH_DIR / f"enrich_batch_{start_no:06d}_{end_no:06d}.csv"
            pd.DataFrame(current_batch).to_csv(batch_path, index=False)
            print(f"Saved last batch: {batch_path.name} | rows: {len(current_batch)}")

        append_failures(failures)
        build_final_output(base_df)

    except KeyboardInterrupt:
        print("\nDihentikan manual. Menyimpan progress yang sudah ada...")
        if current_batch:
            temp_path = ENRICH_BATCH_DIR / f"enrich_batch_interrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            pd.DataFrame(current_batch).to_csv(temp_path, index=False)
            print(f"Saved interrupted batch: {temp_path.name} | rows: {len(current_batch)}")
        append_failures(failures)
        build_final_output(base_df)
        print("Progress aman. Jalankan script lagi untuk melanjutkan.")


if __name__ == "__main__":
    main()
