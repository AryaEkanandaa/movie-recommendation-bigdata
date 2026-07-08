# Nested Movie Chat, History, dan Supabase

Dokumen ini menjelaskan fitur tambahan pada branch `feature/nested-movie-chat`.

## Tujuan

User dapat:

1. meminta rekomendasi film;
2. menekan tombol **Tanya tentang film ini**;
3. membuka child thread yang context-nya terkunci pada satu film;
4. mengajukan beberapa pertanyaan lanjutan;
5. membuka kembali thread melalui menu **History** setelah refresh;
6. login dengan magic link untuk menyinkronkan history ke Supabase.

## Konsep Nesting

Nesting diterapkan pada dua level:

```text
Recommendation thread
└── Movie thread: The Martian
    ├── Message: Ceritanya tentang apa?
    └── Message: Siapa sutradaranya?
```

- `chat_threads.parent_thread_id` menyimpan relasi child thread ke recommendation thread.
- `chat_messages.parent_message_id` menyimpan rantai pesan dalam movie thread.
- `context_movie_id` dan `context_movie` mengunci context film pada child thread.

## Persistence Mode

### Tanpa Supabase

Semua workspace dan movie thread disimpan di `localStorage` browser:

```text
cinematch:workspace:v1
cinematch:movie-threads:v1
```

Mode ini langsung bekerja untuk demo dan tetap bertahan setelah refresh pada browser yang sama.

### Dengan Supabase

Supabase digunakan untuk:

- magic-link authentication;
- PostgreSQL database;
- sinkronisasi history lintas perangkat;
- Row Level Security agar user hanya dapat membaca data miliknya.

Supabase cocok untuk kebutuhan ini karena Auth dan PostgreSQL terintegrasi. Client browser mengirim JWT user secara otomatis, sedangkan RLS membatasi setiap query menggunakan `auth.uid()`.

## Setup Supabase

1. Buat project di Supabase.
2. Buka SQL Editor.
3. Jalankan migration:

```text
supabase/migrations/202607050001_nested_movie_chat.sql
```

4. Pada Authentication URL Configuration, tambahkan `http://localhost:3000`.
5. Isi `.env`:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your_publishable_key
```

6. Build ulang frontend:

```bash
docker compose up -d --build frontend
```

Jangan menggunakan `service_role` key di frontend. Publishable key aman diekspos hanya jika seluruh tabel pada exposed schema dilindungi RLS.

Referensi resmi:

- [Supabase Auth](https://supabase.com/docs/guides/auth)
- [React Auth quickstart](https://supabase.com/docs/guides/auth/quickstarts/react)
- [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)

## Backend Follow-up Endpoint

```text
POST /movies/{movie_id}/chat
```

Request:

```json
{
  "message": "Siapa sutradaranya?",
  "history": [
    {"role": "user", "content": "Ceritanya tentang apa?"},
    {"role": "assistant", "content": "Film ini menceritakan..."}
  ]
}
```

Backend mengambil metadata film berdasarkan `movie_id`, sehingga browser tidak dapat mengganti context dengan metadata palsu. Maksimal 20 pesan diterima schema dan 12 pesan terakhir dikirim sebagai context ke OpenAI.

## Conversation State OpenAI

Project mengelola conversation history sendiri dan mengirim history relevan pada setiap follow-up. Request movie follow-up menggunakan `store=false`.

Responses API juga mendukung `previous_response_id`, tetapi app-owned history dipilih karena:

- history harus tetap tersedia di database aplikasi;
- thread dapat dibuka kembali tanpa bergantung pada retensi response provider;
- context film dan RLS tetap dikontrol aplikasi;
- mode fallback tanpa OpenAI masih dapat membaca metadata film.

Referensi resmi: [OpenAI conversation state](https://developers.openai.com/api/docs/guides/conversation-state#passing-context-from-the-previous-response).

## Fallback Tanpa OpenAI

Jika API key tidak tersedia, pertanyaan dasar tetap dijawab dari metadata: sinopsis, cast, sutradara, genre, rating, dan runtime.

## Security

- Supabase publishable key boleh digunakan di browser; `service_role` key tidak boleh.
- RLS aktif untuk `chat_threads` dan `chat_messages`.
- Semua policy memeriksa `(select auth.uid()) = user_id`.
- `user_id`, `thread_id`, dan `parent_thread_id` memiliki index.
- Backend tidak mempercayai metadata film dari request frontend.
- Pesan dibatasi panjangnya oleh Pydantic.

