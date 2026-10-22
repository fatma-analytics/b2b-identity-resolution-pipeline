# Architecture

```text
Public company API + synthetic contact generator
                 |
        Python idempotent ingestion
                 |
         MinIO / S3 raw Parquet
                 |
   normalize -> blocking -> matching
                 |
   PostgreSQL operational tables
                 |
 ClickHouse analytical tables -> Metabase
                 |
          DQ dashboard and alerts
```

PostgreSQL is the operational store because it provides transactions, constraints and simple upserts for the identity-resolution workflow. ClickHouse is the analytical store because its columnar MergeTree tables and sorted keys are designed for fast scans and aggregations over large event volumes. MinIO makes the object-storage boundary reproducible locally.

Blocking compares only candidates sharing a normalized domain or the first letter of the first name. This avoids an all-to-all comparison and makes the candidate set grow approximately with the number of records per block rather than with the square of the full population. The blocking rule trades a small risk of missed candidates for predictable compute cost; production systems should monitor recall by block.
