# Local Data

Folder ini berisi dataset besar lokal dan tidak di-push ke GitHub.

## Struktur

- `curated/`: dataset hasil preprocessing/enrichment yang menjadi input pipeline final.
- `processed/final/`: dataset final untuk modelling, backend, dan Qdrant payload.
- `processed/vectors/`: vector/embedding film hasil model.
- `raw/`: cadangan lokasi output scraping mentah jika scraping dijalankan ulang.

## Catatan

Karena folder `ml/data/` di-ignore, teman satu tim perlu menaruh dataset lokalnya sendiri atau menjalankan ulang pipeline untuk menghasilkan file di sini.
