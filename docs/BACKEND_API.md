# Backend API

Backend menggunakan FastAPI dan membaca data dari dua sumber:

- `ml/data/processed/final/movies_payload.csv` untuk mencari judul film.
- Qdrant collection `movies` untuk mengambil vector dan mencari film mirip.

## Menjalankan

Pastikan Qdrant sudah terisi dengan vector film, lalu jalankan:

```bash
docker compose up -d qdrant backend
```

API tersedia di:

```text
http://localhost:8000
```

Swagger UI tersedia di:

```text
http://localhost:8000/docs
```

## Endpoint

### Health check

```text
GET /health
```

Memastikan backend dan Qdrant dapat diakses.

### Cari film berdasarkan judul

```text
GET /movies/search?title=batman&limit=10
```

Mengembalikan kandidat judul. Endpoint ini diperlukan karena satu keyword dapat memiliki beberapa film, misalnya Batman.

### Catalog movie default

```text
GET /movies?limit=12
```

Mengembalikan movie list awal untuk user yang baru login atau menekan tombol chat baru. Hasil diurutkan dari kombinasi rating, jumlah vote, popularitas, dan kualitas metadata, sehingga UI tidak kosong sebelum user mengetik query.

### Discovery berdasarkan metadata

```text
GET /movies/discover
```

Filter yang tersedia:

- `genre`: genre film, dapat dikirim lebih dari sekali.
- `actor`: nama aktor.
- `director`: nama sutradara.
- `keyword`: tema atau keyword yang dicari pada keyword, sinopsis, dan tagline.
- `language`: kode ISO 639-1 atau nama bahasa umum, misalnya `ko`, `Korean`, atau `Indonesia`.
- `min_rating` dan `max_rating`: rentang rating 0-10.
- `year_from` dan `year_to`: rentang tahun rilis.
- `min_runtime` dan `max_runtime`: rentang durasi dalam menit.
- `limit`: jumlah hasil, maksimal 50.

Contoh:

```text
GET /movies/discover?actor=Christian%20Bale&genre=action&min_rating=7
GET /movies/discover?language=ko&year_from=2015&max_runtime=130
GET /movies/discover?director=Christopher%20Nolan&keyword=time%20travel
```

Beberapa nilai dalam kategori yang sama menggunakan aturan OR. Kategori yang berbeda menggunakan aturan AND. Sebagai contoh, `genre=action&genre=thriller&actor=Christian Bale` berarti genre action atau thriller, dan aktornya harus Christian Bale.

Endpoint ini tidak membutuhkan film acuan. Hasil diurutkan menggunakan discovery score yang mempertimbangkan rating, jumlah vote, popularitas, dan kualitas metadata.

### Rekomendasi film mirip

```text
GET /recommend/similar?title=Interstellar&top_k=10
```

Alur:

1. Backend mencari film acuan dari payload lokal.
2. Backend mengambil vector film acuan dari Qdrant.
3. Qdrant mencari kandidat vector paling mirip.
4. Backend menerapkan hybrid re-ranking.
5. Backend mengembalikan top recommendation sebagai JSON.

### Chat sederhana

```text
POST /chat
```

Contoh body:

```json
{
  "message": "Saya ingin nonton film seperti Interstellar",
  "top_k": 5
}
```

Tanpa API key, endpoint memakai parser pola untuk mengambil judul setelah kata seperti `mirip`, `seperti`, atau `like`. Mode fallback ini tetap dapat menjalankan rekomendasi tanpa LLM.

Jika `OPENAI_API_KEY` tersedia, endpoint memakai OpenAI Responses API untuk:

1. mengekstrak judul, genre, aktor, sutradara, keyword, bahasa, rating, tahun, dan durasi,
2. menjalankan metadata discovery walaupun user tidak menyebut film acuan,
3. meminta klarifikasi ketika tidak ada judul maupun filter yang dapat digunakan,
4. membuat alasan rekomendasi yang natural berdasarkan kandidat backend.

LLM tidak menentukan atau mengarang daftar film. Pada similarity search, film dipilih oleh Word2Vec, Qdrant, dan hybrid re-ranking. Pada metadata discovery, film dipilih oleh filter dan discovery ranking di backend.

### Chat lanjutan tentang satu film

```text
POST /movies/{movie_id}/chat
```

Endpoint ini digunakan setelah user menekan recommendation card. Backend mengambil metadata film berdasarkan ID dan menjadikannya context tetap untuk percakapan turunan.

```json
{
  "message": "Siapa sutradaranya?",
  "history": [
    {"role": "user", "content": "Ceritanya tentang apa?"},
    {"role": "assistant", "content": "Film ini menceritakan..."}
  ]
}
```

OpenAI menerima metadata film dan maksimal 12 pesan terakhir. Jika OpenAI tidak aktif, backend tetap dapat menjawab pertanyaan dasar dari metadata terstruktur.

Response `/chat` juga memuat `query_analysis` untuk transparansi proses. Field ini berisi:

- `interpreter`: `openai` atau `fallback_pattern`;
- `extracted_intent`: judul, genre, aktor, dan filter yang terdeteksi;
- `execution_mode`: `similarity`, `discovery`, atau `clarification`;
- `backend_query`: ringkasan pipeline yang dijalankan backend;
- `execution_parameters`: collection, candidate pool, top-k, dan formula ranking;
- `steps`: urutan proses dalam bahasa yang mudah dijelaskan saat demo.

Contoh ringkas:

```json
{
  "interpreter": "openai",
  "extracted_intent": {
    "reference_title": "Interstellar",
    "preferred_genres": [],
    "keywords": []
  },
  "execution_mode": "similarity",
  "backend_query": "resolve_title -> Qdrant cosine_search -> hybrid_rerank -> intent_filters -> top_k"
}
```

Untuk permintaan tanpa film acuan, backend memakai filter metadata dan discovery ranking. Untuk permintaan dengan film acuan, Qdrant mencari film mirip terlebih dahulu, kemudian backend menerapkan semua filter.

## OpenAI Setup

Tambahkan key baru ke `.env`:

```env
OPENAI_API_KEY=your_new_key_here
OPENAI_MODEL=gpt-5.4-mini
```

Jangan commit `.env` atau menaruh API key langsung di source code.

## Hybrid Re-Ranking

Backend menggunakan formula yang sama dengan evaluasi ML:

```text
0.70 similarity
+ 0.10 rating
+ 0.08 vote count
+ 0.07 popularity
+ 0.05 metadata quality
```
