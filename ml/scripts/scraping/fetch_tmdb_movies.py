
# # TMDB Scraper 50k–100k (Resume Friendly)
# 
# Notebook ini dibuat untuk mengulang scraping TMDB agar jumlah data bisa naik dari ±13k ke 50k–100k.
# 
# Perubahan utama dibanding notebook lama:
# - Tahun diperluas, bukan hanya 1980–2025.
# - `vote_count.gte` bisa dibuat lebih rendah agar film kecil ikut masuk.
# - Scraping dibagi per bulan supaya tidak mentok limit halaman.
# - Output disimpan per batch/window agar bisa dilanjutkan kalau runtime berhenti.
# - Token tidak di-hardcode; gunakan environment variable atau input aman.


# Untuk install dependency: pip install requests pandas tqdm python-dotenv


import os
import time
import json
import math
import requests
import pandas as pd

from pathlib import Path
from tqdm.auto import tqdm
from datetime import date, datetime, timezone
from getpass import getpass
from dotenv import load_dotenv


# =========================
# CONFIG
# =========================

BASE_URL = "https://api.themoviedb.org/3"

# ML root: file ini disimpan di ml/scripts/scraping/fetch_tmdb_movies.py
# Jadi parents[2] = folder ml
try:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
except NameError:
    PROJECT_ROOT = Path.cwd()

load_dotenv(PROJECT_ROOT / ".env")

TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")

if not TMDB_BEARER_TOKEN:
    TMDB_BEARER_TOKEN = getpass("Paste TMDB Bearer Token: ").strip()

HEADERS = {
    "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
    "accept": "application/json",
}

TARGET_ROWS = int(os.getenv("TARGET_ROWS", "50000"))
START_YEAR = int(os.getenv("START_YEAR", "1900"))
END_YEAR = int(os.getenv("END_YEAR", "2026"))
REQUEST_SLEEP_SECONDS = float(os.getenv("REQUEST_SLEEP_SECONDS", "0.25"))

# Folder output diarahkan ke struktur ml/data
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "tmdb"
BATCH_DIR = DATA_DIR / "discover_batches"
LOG_DIR = DATA_DIR / "failures"

for p in [DATA_DIR, BATCH_DIR, LOG_DIR]:
    p.mkdir(parents=True, exist_ok=True)

print("PROJECT_ROOT:", PROJECT_ROOT)
print("DATA_DIR:", DATA_DIR)
print("TARGET_ROWS:", TARGET_ROWS)
print("YEAR RANGE:", START_YEAR, "-", END_YEAR)


# =========================
# SAFE REQUEST HELPER
# =========================

def tmdb_get(endpoint, params=None, retries=8, sleep_seconds=0.12):
    """
    Request helper yang lebih aman:
    - retry untuk 429 dan error server
    - respect Retry-After kalau tersedia
    - sleep kecil agar tidak terlalu agresif
    """
    url = f"{BASE_URL}{endpoint}"
    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params or {},
                timeout=60
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else (attempt + 1) * 5
                print(f"Rate limited 429. Sleep {wait} seconds...")
                time.sleep(wait)
                continue

            if response.status_code in [500, 502, 503, 504]:
                wait = (attempt + 1) * 3
                print(f"Server error {response.status_code}. Sleep {wait} seconds...")
                time.sleep(wait)
                continue

            response.raise_for_status()
            time.sleep(sleep_seconds)
            return response.json()

        except Exception as e:
            last_error = e
            wait = (attempt + 1) * 3
            time.sleep(wait)

    raise last_error


# =========================
# GENRE MAP
# =========================

def get_genre_map(language="en-US"):
    data = tmdb_get("/genre/movie/list", params={"language": language})
    return {g["id"]: g["name"] for g in data.get("genres", [])}

GENRE_MAP = get_genre_map()
GENRE_MAP


# =========================
# UTILITIES
# =========================

def genre_ids_to_names(genre_ids, genre_map):
    if not isinstance(genre_ids, list):
        return ""
    return ", ".join([genre_map.get(gid, str(gid)) for gid in genre_ids])

def movie_to_row(movie, source_config, source_start_date, source_end_date, source_page):
    genre_ids = movie.get("genre_ids") or []
    return {
        "id": movie.get("id"),
        "title": movie.get("title"),
        "original_title": movie.get("original_title"),
        "original_language": movie.get("original_language"),
        "overview": movie.get("overview"),
        "release_date": movie.get("release_date"),
        "genre_ids": ",".join(map(str, genre_ids)),
        "genres": genre_ids_to_names(genre_ids, GENRE_MAP),
        "popularity": movie.get("popularity"),
        "vote_average": movie.get("vote_average"),
        "vote_count": movie.get("vote_count"),
        "adult": movie.get("adult"),
        "video": movie.get("video"),
        "poster_path": movie.get("poster_path"),
        "backdrop_path": movie.get("backdrop_path"),
        "source_config": source_config,
        "source_start_date": source_start_date,
        "source_end_date": source_end_date,
        "source_page": source_page,
        "collected_at": datetime.now(timezone.utc).isoformat()
    }

def month_windows(start_year, end_year):
    """
    Return window bulanan: YYYY-MM-DD s/d YYYY-MM-DD.
    Pakai primary_release_date.gte/lte agar query tidak terlalu besar.
    """
    windows = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            start = date(y, m, 1)
            if m == 12:
                end = date(y, 12, 31)
            else:
                end = date(y, m + 1, 1) - pd.Timedelta(days=1)
                # pandas Timedelta membuat hasil tetap kompatibel untuk date
                # di beberapa versi pandas hasilnya sudah datetime.date, jadi tidak perlu .date() lagi
            windows.append((start.isoformat(), end.isoformat()))
    return windows

def combine_discover_batches():
    files = sorted(BATCH_DIR.glob("discover_*.csv"))
    frames = []
    for f in files:
        try:
            frames.append(pd.read_csv(f))
        except Exception as e:
            print("Gagal baca:", f.name, e)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["id"]).reset_index(drop=True)

    if "release_date" in df.columns:
        df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")

    return df


# =========================
# DISCOVER SCRAPER PER WINDOW
# =========================

MAX_TMDB_PAGES = 500  # TMDB page max
RESULTS_PER_PAGE = 20

def discover_movies_by_date_window(
    start_date,
    end_date,
    config_name,
    sort_by="popularity.desc",
    min_vote_count=0,
    include_adult=False,
    include_video=False,
    language="en-US",
    original_language=None,
    overwrite=False,
):
    safe_start = start_date.replace("-", "")
    safe_end = end_date.replace("-", "")
    batch_file = BATCH_DIR / f"discover_{config_name}_{safe_start}_{safe_end}.csv"

    if batch_file.exists() and not overwrite:
        return pd.read_csv(batch_file)

    base_params = {
        "primary_release_date.gte": start_date,
        "primary_release_date.lte": end_date,
        "sort_by": sort_by,
        "vote_count.gte": min_vote_count,
        "include_adult": str(include_adult).lower(),
        "include_video": str(include_video).lower(),
        "language": language,
    }

    if original_language:
        base_params["with_original_language"] = original_language

    # First request untuk tahu total_pages
    first_params = dict(base_params)
    first_params["page"] = 1

    data = tmdb_get("/discover/movie", params=first_params)
    total_pages = min(int(data.get("total_pages", 0) or 0), MAX_TMDB_PAGES)

    rows = []
    seen = set()

    def consume_page(page_data, page_no):
        for movie in page_data.get("results", []) or []:
            movie_id = movie.get("id")
            if movie_id and movie_id not in seen:
                seen.add(movie_id)
                rows.append(
                    movie_to_row(
                        movie=movie,
                        source_config=config_name,
                        source_start_date=start_date,
                        source_end_date=end_date,
                        source_page=page_no,
                    )
                )

    consume_page(data, 1)

    for page in range(2, total_pages + 1):
        params = dict(base_params)
        params["page"] = page
        page_data = tmdb_get("/discover/movie", params=params)
        consume_page(page_data, page)

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.drop_duplicates(subset=["id"]).reset_index(drop=True)

    df.to_csv(batch_file, index=False)
    return df


# =========================
# RUN DISCOVER SCRAPING
# =========================

# TARGET_ROWS, START_YEAR, dan END_YEAR dibaca dari .env di bagian CONFIG

# Saran:
# - Pass 1 min_vote_count=10: kualitas data lebih bagus, film sangat kosong lebih sedikit
# - Pass 2 min_vote_count=0 : untuk mengejar jumlah kalau belum mencapai target
RUN_CONFIGS = [
    {
        "config_name": "vote10",
        "min_vote_count": 10,
        "sort_by": "popularity.desc",
        "include_adult": False,
        "include_video": False,
        "original_language": None,
    },
    {
        "config_name": "vote0",
        "min_vote_count": 0,
        "sort_by": "popularity.desc",
        "include_adult": False,
        "include_video": False,
        "original_language": None,
    },
]

windows = month_windows(START_YEAR, END_YEAR)

for cfg in RUN_CONFIGS:
    print("\n=== RUN CONFIG:", cfg["config_name"], "===")

    for start_date, end_date in tqdm(windows, desc=f"Scraping {cfg['config_name']}"):
        df_current = combine_discover_batches()
        current_rows = len(df_current)

        if current_rows >= TARGET_ROWS:
            print(f"Target tercapai: {current_rows:,} rows")
            break

        try:
            df_window = discover_movies_by_date_window(
                start_date=start_date,
                end_date=end_date,
                config_name=cfg["config_name"],
                sort_by=cfg["sort_by"],
                min_vote_count=cfg["min_vote_count"],
                include_adult=cfg["include_adult"],
                include_video=cfg["include_video"],
                original_language=cfg["original_language"],
            )

            if len(df_window) > 0:
                print(f"{start_date} - {end_date}: +{len(df_window)} rows | total now approx {current_rows + len(df_window):,}")

        except Exception as e:
            fail_log = LOG_DIR / "discover_failures.csv"
            fail_df = pd.DataFrame([{
                "config_name": cfg["config_name"],
                "start_date": start_date,
                "end_date": end_date,
                "error": str(e),
                "failed_at": datetime.now(timezone.utc).isoformat()
            }])
            fail_df.to_csv(fail_log, mode="a", header=not fail_log.exists(), index=False)
            print("FAILED:", start_date, end_date, e)

    df_after_config = combine_discover_batches()
    if len(df_after_config) >= TARGET_ROWS:
        break

df_movies = combine_discover_batches()
df_movies = df_movies.sort_values(["popularity", "vote_count"], ascending=False).drop_duplicates(subset=["id"]).reset_index(drop=True)
df_movies = df_movies.head(TARGET_ROWS)

base_file = DATA_DIR / f"tmdb_movies_base_{len(df_movies)}.csv"
df_movies.to_csv(base_file, index=False)

print("Final base rows:", len(df_movies))
print("Saved:", base_file)
df_movies.head()



# ## Enrichment opsional
# 
# Kalau jumlah base movie sudah cukup, baru jalankan enrichment. Untuk tugas rekomendasi, biasanya base data dulu dibuat besar, lalu enrichment dilakukan bertahap. Jangan langsung enrichment 100k kalau belum perlu, karena detail + cast/crew/keywords berarti request lebih banyak.


# =========================
# ENRICHMENT OPTIONAL
# =========================

ENRICH_DIR = DATA_DIR / "enrichment"
ENRICH_BATCH_DIR = ENRICH_DIR / "batches"
for p in [ENRICH_DIR, ENRICH_BATCH_DIR]:
    p.mkdir(parents=True, exist_ok=True)

def get_movie_detail_bundle(movie_id, language="en-US"):
    return tmdb_get(
        f"/movie/{int(movie_id)}",
        params={
            "language": language,
            "append_to_response": "credits,keywords"
        },
        retries=8,
        sleep_seconds=0.15,
    )

def unique_join(values, sep=", "):
    seen = []
    for v in values:
        if v and v not in seen:
            seen.append(v)
    return sep.join(seen)

def extract_movie_enrichment(detail):
    credits = detail.get("credits", {}) or {}
    cast = credits.get("cast", []) or []
    crew = credits.get("crew", []) or []
    keywords = (detail.get("keywords", {}) or {}).get("keywords", []) or []

    directors = [c for c in crew if c.get("job") == "Director"]
    writers = [c for c in crew if c.get("job") in ["Writer", "Screenplay", "Story"]]
    top_cast = sorted(cast, key=lambda x: (x.get("order", 9999), x.get("cast_id", 9999)))

    return {
        "id": detail.get("id"),
        "runtime": detail.get("runtime"),
        "status": detail.get("status"),
        "tagline": detail.get("tagline"),
        "budget": detail.get("budget"),
        "revenue": detail.get("revenue"),
        "imdb_id": detail.get("imdb_id"),
        "homepage": detail.get("homepage"),
        "production_companies": unique_join([(pc or {}).get("name") for pc in detail.get("production_companies", []) or []]),
        "production_countries": unique_join([(pc or {}).get("iso_3166_1") for pc in detail.get("production_countries", []) or []]),
        "spoken_languages": unique_join([(lang or {}).get("english_name") for lang in detail.get("spoken_languages", []) or []]),
        "director": unique_join([d.get("name") for d in directors]),
        "writers": unique_join([w.get("name") for w in writers]),
        "top_cast": unique_join([c.get("name") for c in top_cast[:10]]),
        "keywords": unique_join([k.get("name") for k in keywords]),
    }

def existing_enriched_ids():
    path = ENRICH_DIR / "movie_enrichment_master.csv"
    if not path.exists():
        return set()
    old = pd.read_csv(path, usecols=["id"])
    return set(old["id"].dropna().astype(int).tolist())

def append_csv(df, path):
    if df.empty:
        return
    df.to_csv(path, mode="a", header=not path.exists(), index=False)

def enrich_movies(df_source, target_enrich_rows=None, batch_size=100):
    movie_ids = df_source["id"].dropna().astype(int).drop_duplicates().tolist()

    if target_enrich_rows:
        movie_ids = movie_ids[:target_enrich_rows]

    done = existing_enriched_ids()
    target_ids = [mid for mid in movie_ids if mid not in done]

    print(f"Source IDs        : {len(movie_ids):,}")
    print(f"Already enriched : {len(done):,}")
    print(f"Remaining        : {len(target_ids):,}")

    master_file = ENRICH_DIR / "movie_enrichment_master.csv"
    fail_file = ENRICH_DIR / "movie_enrichment_failures.csv"

    for batch_no, start_idx in enumerate(range(0, len(target_ids), batch_size), start=1):
        batch_ids = target_ids[start_idx:start_idx + batch_size]
        rows = []
        failures = []

        for mid in tqdm(batch_ids, desc=f"Enrich batch {batch_no}"):
            try:
                detail = get_movie_detail_bundle(mid)
                rows.append(extract_movie_enrichment(detail))
            except Exception as e:
                failures.append({
                    "movie_id": mid,
                    "error": str(e),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "batch_no": batch_no,
                })

        df_rows = pd.DataFrame(rows)
        df_fail = pd.DataFrame(failures)

        append_csv(df_rows, master_file)
        append_csv(df_fail, fail_file)

        df_rows.to_csv(ENRICH_BATCH_DIR / f"enrich_batch_{batch_no:05d}.csv", index=False)

        print(f"[BATCH {batch_no}] success={len(df_rows)} failed={len(df_fail)}")

# Contoh:
# enrich_movies(df_movies, target_enrich_rows=50_000, batch_size=100)


# =========================
# COMBINE FINAL ENRICHED FILE
# =========================

enrich_file = ENRICH_DIR / "movie_enrichment_master.csv"

if enrich_file.exists():
    df_enrich = pd.read_csv(enrich_file).drop_duplicates(subset=["id"], keep="last")
    df_final = df_movies.merge(df_enrich, on="id", how="left")
else:
    df_final = df_movies.copy()

final_file = DATA_DIR / f"tmdb_movies_final_{len(df_final)}.csv"
df_final.to_csv(final_file, index=False)

print("Final rows:", len(df_final))
print("Saved:", final_file)
df_final.head()



# ## Download output di Colab
# 
# Jalankan cell di bawah hanya kalau sudah selesai.


# from google.colab import files
# files.download(str(final_file))
