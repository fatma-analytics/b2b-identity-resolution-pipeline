# Performance note

The repository contains the PostgreSQL and ClickHouse DDL plus equivalent analytical query shapes. Docker services are provided for a local benchmark, but no artificial timing claim is published: query timings depend on the user's CPU, disk and loaded volume. Run the same query against both services and record `EXPLAIN` output before claiming a speed-up. ClickHouse should benefit from its columnar layout and `(source, resolved_person_id, signal_id)` order for source and identity aggregations.
