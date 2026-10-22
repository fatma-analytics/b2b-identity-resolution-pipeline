# Ingestion

`build_project.py` demonstrates an idempotent run: it rewrites deterministic outputs from a fixed synthetic seed, stores the public company extract in `data/raw/public_companies.csv`, and keeps a truth key only in the synthetic signal layer. A production version would upload Parquet objects to MinIO with a source and update-date partition, then upsert an `ingestion_log` table.
