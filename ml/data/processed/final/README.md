# Final Processed Data

File di folder ini dibuat oleh:

```bash
docker compose run --rm ml python ml/scripts/preprocessing/finalize_datasets.py
```

Output:

- `movies_final.csv`: dataset utama untuk training/evaluasi.
- `movies_payload.csv`: metadata ringkas untuk Qdrant/backend.
