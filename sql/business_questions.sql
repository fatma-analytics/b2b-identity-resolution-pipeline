-- Product question 1: what share of signals resolves to a profile?
SELECT source, count() AS signals, countIf(confidence >= 0.85) AS high_confidence, high_confidence / signals AS high_confidence_rate FROM resolved_identities GROUP BY source;
-- Product question 2: which source has the weakest domain coverage?
SELECT source, avg(domain_norm != '') AS domain_coverage FROM signals_normalized GROUP BY source ORDER BY domain_coverage;
-- Product question 3: how fresh is the latest signal by source?
SELECT source, max(loaded_at) AS latest_loaded_at, dateDiff('hour', max(loaded_at), now()) AS freshness_hours FROM raw_signals GROUP BY source;
-- Product question 4: confidence distribution for review queue.
SELECT source, quantile(0.5)(confidence) AS p50_confidence, countIf(confidence < 0.85) AS review_queue FROM resolved_identities GROUP BY source;
