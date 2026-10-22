# Data quality controls

The pipeline records results in `quality/dq_results.csv` and JSON. Controls cover freshness, row volume, email validity, signal-key uniqueness, company-domain completeness, matching precision, resolution coverage and confidence completeness.

Raw checks stop ingestion when the source is stale or empty. Clean checks quarantine malformed emails and duplicate signal IDs. Resolved checks keep a review queue when precision falls below 0.85, coverage below 0.95 or confidence is missing. The demo has one intentional clean-stage failure because the event source contains blank domains; that failure is visible rather than silently hidden.
