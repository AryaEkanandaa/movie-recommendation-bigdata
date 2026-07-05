# Pertanyaan Kritis Dosen dan Jawabannya

Dokumen ini adalah bahan latihan sidang atau presentasi. Jangan menghafal setiap kalimat. Pahami alur dan gunakan jawaban singkat terlebih dahulu. Berikan detail teknis hanya jika dosen mengejar.

## Ringkasan 30 Detik

> Sistem ini adalah content-based movie recommendation. Metadata sekitar 80 ribu film dibersihkan dan digabung menjadi `movie_document_weighted`, kemudian PySpark Word2Vec mengubah setiap film menjadi vector 64 dimensi. Vector dan metadata disimpan di Qdrant. Saat user menyebut film acuan, Qdrant melakukan cosine similarity search dan backend menjalankan hybrid re-ranking. Jika user memberikan kriteria tanpa film acuan, backend menjalankan metadata discovery. OpenAI hanya memahami bahasa natural dan menjelaskan hasil; daftar film tetap ditentukan backend.

## Angka Yang Perlu Diingat

| Item | Nilai |
| --- | ---: |
| Jumlah film terlatih dan terindeks | 80.290 |
| Dimensi vector Word2Vec | 64 |
| Ukuran vocabulary | 82.793 |
| Rata-rata token setelah filtering | 91,7755 |
| `minCount` Word2Vec | 5 |
| Iterasi Word2Vec | 5 |
| Query evaluasi | 9 |
| Total rekomendasi evaluasi | 90 |
| Rata-rata similarity Word2Vec | 0,8921 |
| Rata-rata hybrid score | 0,7613 |
| Rata-rata genre overlap | 0,5671 |
| Rata-rata rating rekomendasi | 7,1796 |

## Model dan Pendekatan

### 1. Model yang kalian gunakan sebenarnya apa?

**Jawaban singkat:**

Model utama adalah content-based recommendation menggunakan PySpark ML Word2Vec. Model mengubah gabungan metadata setiap film menjadi vector 64 dimensi.

**Jika dikejar:**

Input model adalah `movie_document_weighted`, berisi title, genre, sutradara, cast, keyword, overview, dan tagline. Qdrant bukan model, melainkan vector database untuk mencari vector terdekat menggunakan cosine similarity.

### 2. Apakah OpenAI yang memberikan rekomendasi?

**Jawaban singkat:**

Tidak. OpenAI hanya mengekstrak intent dan membuat penjelasan. Film dipilih oleh Word2Vec, Qdrant, filter backend, dan ranking.

**Jika dikejar:**

Kandidat yang diberikan kepada OpenAI sudah dibatasi oleh backend. Prompt melarang menambah atau mengganti film. ID hasil LLM juga dicocokkan kembali dengan kandidat, sehingga film di luar kandidat tidak dimasukkan.

### 3. Jadi modelnya buatan sendiri atau hanya memakai API?

**Jawaban singkat:**

Model rekomendasinya dilatih sendiri dari corpus metadata film menggunakan PySpark Word2Vec. OpenAI adalah komponen antarmuka bahasa, bukan pengganti model rekomendasi.

### 4. Mengapa menggunakan content-based recommendation?

**Jawaban singkat:**

Dataset tidak memiliki `user_id`, histori menonton, klik, atau rating personal. Karena itu collaborative filtering belum dapat dilatih secara valid.

**Jika dikejar:**

Content-based dapat bekerja hanya dengan metadata item dan juga dapat menjelaskan kemiripan melalui genre, cast, sutradara, keyword, dan sinopsis.

### 5. Mengapa tidak menggunakan collaborative filtering?

Collaborative filtering membutuhkan matriks interaksi user-film. Membuat data interaksi palsu akan menghasilkan evaluasi yang tidak dapat dipertanggungjawabkan. Collaborative filtering menjadi pengembangan berikutnya setelah aplikasi mengumpulkan feedback nyata.

### 6. Bagaimana Word2Vec bekerja dalam proyek ini?

Word2Vec mempelajari kata-kata yang sering muncul dalam konteks serupa pada corpus film. Setelah tokenisasi dan stop-word removal, PySpark membentuk representasi kata lalu menghasilkan vector dokumen film. Film dengan konteks metadata serupa diharapkan berada berdekatan dalam ruang vector.

### 7. Mengapa dimensi vector-nya 64?

Dimensi 64 dipilih sebagai kompromi untuk dataset sekitar 80 ribu film: cukup padat untuk menyimpan informasi konteks, tetapi tetap ringan untuk penyimpanan dan similarity search. Nilai ini masih hyperparameter dan idealnya dibandingkan dengan 32, 128, atau 256 pada eksperimen lanjutan.

### 8. Mengapa model tidak disimpan sebagai `.pkl`?

Model dibuat dengan PySpark ML, sehingga disimpan menggunakan format native `model.save()` sebagai folder model. Vector hasil transformasi disimpan dalam Parquet dan kemudian diindeks ke Qdrant. `.pkl` lebih umum untuk objek Python atau scikit-learn dan bukan kewajiban sebuah model ML.

### 9. Saat aplikasi berjalan, apakah Word2Vec dilatih ulang?

Tidak. Training dan indexing adalah proses offline. Saat runtime, backend mengambil vector film yang sudah tersimpan di Qdrant. Model Word2Vec hanya dibutuhkan lagi ketika dataset diperbarui atau vector perlu dibuat ulang.

## Perbandingan Model

### 10. Mengapa membandingkan CountVectorizer, TF-IDF, dan Word2Vec?

CountVectorizer menjadi baseline frekuensi kata, TF-IDF mengurangi pengaruh kata umum dan menonjolkan kata informatif, sedangkan Word2Vec menghasilkan dense vector yang menangkap kedekatan konteks. Perbandingan menunjukkan alasan pemilihan model runtime, bukan sekadar memilih model paling kompleks.

### 11. Mengapa Word2Vec dipilih jika genre overlap CountVectorizer lebih tinggi?

CountVectorizer memang menghasilkan genre overlap rata-rata 0,5928, sedikit lebih tinggi dari Word2Vec 0,5671. Namun Word2Vec menghasilkan rata-rata rating 7,1796 dan vote count 7.034, lebih tinggi pada evaluasi ini, serta menghasilkan dense vector yang cocok untuk Qdrant dan pencarian runtime. Pemilihan mempertimbangkan relevansi, kualitas kandidat, dan kebutuhan deployment.

### 12. Word2Vec memiliki skor 0,8921 sedangkan TF-IDF 0,2566. Apakah berarti Word2Vec tiga kali lebih bagus?

Tidak. Skor cosine dari representasi yang berbeda tidak boleh dibandingkan secara mentah karena distribusi dan kalibrasi ruang vector berbeda. Perbandingan yang lebih bermakna menggunakan genre overlap, kualitas hasil, evaluasi manual, latency, dan metric berbasis ground truth jika tersedia.

### 13. Apa fungsi K-Means dalam proyek ini?

K-Means dipakai untuk eksplorasi segmentasi atau pengelompokan film, bukan sebagai model rekomendasi runtime. Cluster dapat membantu memahami kelompok konten, tetapi anggota satu cluster belum tentu merupakan tetangga paling relevan untuk sebuah film.

### 14. Apa perbedaan TF-IDF dan Word2Vec secara sederhana?

TF-IDF melihat seberapa penting kata tertentu dalam sebuah dokumen dibandingkan seluruh corpus. Word2Vec mencoba mempelajari kedekatan konteks antarkata. TF-IDF biasanya kuat untuk kecocokan kata eksplisit, sedangkan Word2Vec lebih fleksibel terhadap konteks yang serupa.

## Retrieval, Qdrant, dan Ranking

### 15. Mengapa memakai Qdrant?

Qdrant dirancang untuk approximate nearest-neighbor vector search, mendukung cosine distance, metadata payload, filtering, dan mudah dijalankan melalui Docker. PostgreSQL biasa tetap berguna untuk user, watchlist, dan transaksi, tetapi kebutuhan utama MVP adalah pencarian vector.

### 16. Apakah Qdrant adalah database utama sekaligus model?

Qdrant adalah database/index pencarian, bukan model pembelajaran. Model Word2Vec menghasilkan vector; Qdrant menyimpan dan mencari vector tersebut.

### 17. Bagaimana cosine similarity bekerja?

Cosine similarity membandingkan arah dua vector, bukan panjangnya. Nilai mendekati 1 berarti arah vector semakin mirip. Dalam sistem ini, skor tinggi menunjukkan metadata dan konteks film yang relatif berdekatan, bukan jaminan bahwa setiap user akan menyukai film tersebut.

### 18. Mengapa perlu hybrid re-ranking jika sudah ada similarity?

Similarity hanya mengukur kedekatan konten. Hybrid re-ranking menambahkan rating, vote count, popularity, dan kualitas metadata supaya kandidat yang mirip tetapi datanya lemah tidak selalu berada di atas.

Formula runtime:

```text
0.70 * similarity
+ 0.10 * rating_norm
+ 0.08 * vote_count_norm
+ 0.07 * popularity_norm
+ 0.05 * quality_norm
```

### 19. Dari mana bobot hybrid tersebut berasal?

Bobot ditentukan secara heuristik untuk MVP, dengan similarity tetap dominan sebesar 70%. Bobot tersebut belum dipelajari dari feedback user. Pengembangan yang lebih kuat adalah tuning berbasis validation set atau learning-to-rank setelah tersedia data interaksi.

### 20. Apakah hybrid ranking tidak membuat film populer selalu menang?

Risiko itu ada. Karena itu kontribusi similarity dibuat paling besar dan popularity hanya 7%. Namun popularity bias belum hilang sepenuhnya. Evaluasi diversity, novelty, dan long-tail coverage diperlukan pada versi berikutnya.

### 21. Apa perbedaan similarity search dan metadata discovery?

Similarity search membutuhkan film acuan dan mencari vector terdekat melalui Qdrant. Metadata discovery tidak membutuhkan film acuan; backend memfilter genre, aktor, sutradara, keyword, bahasa, rating, tahun, dan durasi, kemudian mengurutkan hasil berdasarkan discovery score.

### 22. Bagaimana filter gabungan bekerja?

LLM mengubah bahasa user menjadi schema terstruktur. Backend melakukan OR dalam kategori yang sama dan AND antarkategori. Contohnya, genre action atau thriller dengan aktor Christian Bale berarti film harus memenuhi salah satu genre sekaligus memiliki aktor tersebut.

### 23. Mengapa metadata discovery masih memakai Pandas, bukan Qdrant filtering?

Untuk MVP 80 ribu film, pemrosesan in-memory masih sederhana dan cukup cepat. Qdrant tetap menyimpan payload dan dapat digunakan untuk filtering pada tahap optimasi. Jika data tumbuh besar atau backend direplikasi, metadata sebaiknya dipindahkan ke filter Qdrant atau database relasional agar sumber data runtime lebih terpusat.

## LLM dan RAG

### 24. Apakah sistem ini termasuk RAG?

Ya, dalam bentuk retrieval-augmented generation ringan. Sistem mengambil film dari data sendiri terlebih dahulu, lalu memberikan kandidat tersebut sebagai konteks kepada LLM untuk dijelaskan. Ini bukan RAG dokumen panjang dan LLM bukan retriever utama.

### 25. Bagaimana mencegah halusinasi LLM?

LLM menerima kandidat terbatas dari backend, menggunakan structured output, dan diwajibkan mengembalikan ID kandidat yang tepat. Backend hanya menerapkan alasan untuk ID yang memang ada. Walaupun risiko bahasa yang tidak akurat masih ada, LLM tidak diberi wewenang mengganti daftar film.

### 26. Apa yang terjadi jika OpenAI mati atau API key habis?

Backend memiliki fallback parser untuk permintaan sederhana berbasis judul. Endpoint pencarian judul, metadata discovery, similarity search, dan Qdrant tetap dapat digunakan tanpa LLM. Yang berkurang adalah pemahaman bahasa kompleks dan penjelasan natural.

### 27. Mengapa memakai OpenAI dan bukan melatih LLM sendiri?

Tujuan penelitian ini adalah sistem rekomendasi, bukan pelatihan foundation model. Melatih LLM membutuhkan corpus, GPU, waktu, dan biaya yang tidak sebanding dengan ruang lingkup tugas. OpenAI dipakai hanya untuk intent parsing dan natural-language generation.

### 28. Apakah mengirim data sensitif ke OpenAI?

Permintaan yang dikirim hanya teks pencarian user serta metadata kandidat film. Sistem saat ini tidak membutuhkan data pribadi. API key disimpan di environment variable dan tidak boleh masuk source code atau Git.

## Data dan Big Data

### 29. Data berasal dari mana dan berapa jumlahnya?

Data berasal dari TMDB melalui scraping dan enrichment API. Setelah preprocessing, 80.290 film memiliki dokumen valid, vector Word2Vec, dan point di collection Qdrant `movies`.

### 30. Mengapa disebut Big Data jika hanya 80 ribu baris?

Jumlah baris bukan satu-satunya aspek. Setiap film membawa metadata teks, cast, keyword, overview, dan vector. Proyek menggunakan pipeline terdistribusi PySpark dan vector indexing. Namun kami tidak mengklaim skala ini setara sistem industri; 80 ribu film adalah skala akademik untuk membuktikan pipeline yang dapat dikembangkan.

### 31. Mengapa memakai PySpark? Bukankah Pandas cukup?

Untuk 80 ribu film, Pandas memang masih mampu. PySpark dipilih untuk membangun pipeline yang konsisten dengan mata kuliah Big Data, memanfaatkan Spark ML, partisi, dan pola pemrosesan yang dapat ditingkatkan skalanya. Jawaban yang jujur adalah PySpark memberi nilai arsitektural dan skalabilitas, bukan karena laptop tidak mampu membuka datanya.

### 32. Bagaimana menangani data kosong dan duplikat?

Pipeline preprocessing membersihkan teks, menggabungkan scraping dan enrichment, memvalidasi `id`, `title`, `movie_document_weighted`, dan genre, serta membuang record yang tidak memenuhi syarat training. Ringkasan kualitas data disimpan dalam report preprocessing dan data summary.

### 33. Apakah ada data leakage?

Model ini unsupervised content-based dan tidak memprediksi label masa depan, sehingga konsep leakage berbeda dari supervised learning. Namun evaluasi tetap harus hati-hati: metadata seperti popularity dan rating digunakan dalam re-ranking dan juga dinilai sebagai kualitas hasil, sehingga keduanya bukan bukti independen bahwa user menyukai rekomendasi.

### 34. Bagaimana menangani film baru?

Film baru perlu melalui enrichment, preprocessing, transformasi Word2Vec, dan indexing ke Qdrant. Jika kosakatanya sudah dikenal model, vector dapat dibuat tanpa melatih ulang; jika banyak istilah baru atau distribusi data berubah, model sebaiknya dilatih dan diindeks ulang.

### 35. Mengapa ada film yang belum rilis di hasil rekomendasi?

Dataset TMDB dapat mencakup film berstatus upcoming. Saat ini sistem belum selalu memfilter status atau tanggal rilis terhadap tanggal hari ini. Ini adalah keterbatasan data yang jelas dan dapat diperbaiki dengan filter `status=Released` serta `release_date <= today`.

## Evaluasi

### 36. Bagaimana kalian tahu rekomendasinya bagus?

Evaluasi saat ini menggunakan sembilan film acuan dan sepuluh rekomendasi per query. Metric yang dicatat meliputi similarity, hybrid score, genre overlap, rating, dan vote count, ditambah inspeksi contoh hasil. Ini cukup untuk evaluasi MVP, tetapi belum membuktikan kepuasan user.

### 37. Mengapa tidak memakai accuracy?

Rekomendasi bukan klasifikasi dengan satu jawaban benar. Metric yang lebih sesuai adalah Precision@K, Recall@K, NDCG, MAP, diversity, novelty, atau evaluasi user. Karena belum ada ground truth interaksi, proyek menggunakan proxy metric dan evaluasi manual.

### 38. Apakah evaluasi sembilan query sudah cukup?

Belum untuk kesimpulan umum. Sembilan query digunakan sebagai smoke evaluation lintas genre. Evaluasi lanjutan harus menambah jumlah query, membuat relevance judgment, dan melibatkan user study atau data interaksi nyata.

### 39. Mengapa hasil Parasite memiliki rata-rata rating lebih rendah daripada query lain?

Itu menunjukkan kelemahan yang nyata: similarity konteks tidak selalu menghasilkan kandidat dengan kualitas atau relevansi yang sama. Hasil tersebut menjadi alasan adanya hybrid ranking dan filter, sekaligus bukti bahwa sistem belum sempurna. Kami tidak menyembunyikan hasil yang kurang baik karena itu penting untuk menentukan pengembangan berikutnya.

### 40. Apakah genre overlap cukup untuk mengukur relevansi?

Tidak. Genre overlap hanya salah satu proxy. Dua film dapat relevan karena tema, sutradara, cast, suasana, atau struktur cerita meskipun genre tidak identik. Sebaliknya, genre sama tidak menjamin film terasa mirip.

## Arsitektur dan Deployment

### 41. Mengapa memakai Docker?

Docker menyamakan versi Python, Java/PySpark, dependency, backend, frontend, dan Qdrant. Dengan Compose, anggota kelompok dapat menjalankan layanan yang sama tanpa setup manual yang berbeda-beda.

### 42. Bagaimana sistem berjalan saat hosting jika tidak ada file `.pkl`?

Runtime tidak membutuhkan `.pkl`. Backend membaca metadata final dan mengambil vector dari Qdrant. Model PySpark serta Parquet adalah artefak training untuk reproduksi dan re-indexing, sedangkan Qdrant menjadi artefak serving vector.

### 43. Apa bottleneck sistem saat ini?

Bottleneck potensial adalah panggilan OpenAI, loading CSV ke memori, dan jumlah kandidat Qdrant sebelum filtering. Optimasi berikutnya adalah caching, Qdrant payload filtering, pagination, asynchronous request, dan observability latency.

### 44. Bagaimana jika jumlah data menjadi jutaan film?

Training dapat memakai cluster Spark, Qdrant dapat di-shard, filtering dipindahkan dari Pandas ke Qdrant atau database terindeks, dan backend dibuat stateless agar dapat direplikasi. Pipeline saat ini menunjukkan pola komponennya, tetapi belum diuji pada skala jutaan.

### 45. Apa kekurangan paling besar dari sistem ini?

Belum ada personalisasi berbasis perilaku user dan belum ada ground truth evaluasi. Sistem memahami kemiripan konten, bukan selera individual. Kekurangan berikutnya adalah bobot hybrid masih heuristik, keyword matching masih literal, dan ketergantungan LLM menambah biaya serta latency.

### 46. Kalau diberi waktu tambahan, apa prioritas pengembangannya?

1. Mengumpulkan feedback suka/tidak suka dan riwayat interaksi.
2. Menambahkan evaluasi Precision@K, Recall@K, NDCG, diversity, dan user study.
3. Memindahkan filter metadata ke Qdrant atau PostgreSQL.
4. Menambahkan diversity re-ranking dan mengurangi popularity bias.
5. Membandingkan Word2Vec dengan sentence embedding modern.

## Pertanyaan Jebakan dan Jawaban Aman

### “Berarti similarity 0,9 sama dengan akurasi 90%?”

Tidak. Similarity adalah kedekatan arah vector, bukan probabilitas dan bukan accuracy.

### “Berarti Word2Vec pasti lebih bagus karena skornya paling tinggi?”

Tidak. Skor antarmodel tidak terkalibrasi pada skala yang sama. Keputusan harus melihat metric relevansi, kualitas hasil, dan kebutuhan deployment.

### “Apakah LLM menjamin alasannya benar?”

Tidak menjamin. Sistem membatasi konteks dan kandidat untuk mengurangi halusinasi, tetapi penjelasan tetap perlu dianggap sebagai natural-language explanation, bukan fakta baru di luar metadata.

### “Apakah sistem ini sudah production-ready?”

Belum. Ini MVP akademik yang fungsional. Production membutuhkan autentikasi, rate limiting, monitoring, backup, secret management, load testing, dan evaluasi user nyata.

### “Apakah PySpark wajib untuk 80 ribu data?”

Tidak wajib dari sisi kapasitas. PySpark dipilih untuk Spark ML, reproduksibilitas pipeline Big Data, dan jalur scaling, bukan karena Pandas sama sekali tidak mampu.

## Kalimat Yang Sebaiknya Dihindari

Hindari klaim berikut:

- “Similarity 0,89 berarti accuracy 89%.”
- “Word2Vec pasti paling baik karena skornya paling tinggi.”
- “LLM kami yang menentukan rekomendasi.”
- “Sistem ini sudah tidak bisa berhalusinasi.”
- “Sistem sudah memahami selera setiap user.”
- “Sistem sudah production-ready.”
- “PySpark wajib karena 80 ribu baris tidak bisa diproses Pandas.”

Gunakan bentuk yang lebih tepat:

- “Hasil evaluasi MVP menunjukkan...”
- “Pada konfigurasi dan query pengujian kami...”
- “Sistem mengurangi risiko halusinasi dengan membatasi kandidat...”
- “Keterbatasan saat ini adalah...”
- “Pengembangan berikutnya yang paling relevan adalah...”

## Penutup Presentasi

> Kontribusi utama proyek ini bukan sekadar chatbot, melainkan pipeline rekomendasi end-to-end: pengumpulan dan enrichment data, preprocessing PySpark, training Word2Vec, vector serving dengan Qdrant, hybrid ranking, metadata filtering, backend API, dan antarmuka LLM. Kami juga dapat menunjukkan keterbatasannya secara terukur dan jalur pengembangannya berdasarkan data interaksi nyata.
