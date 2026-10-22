# Quality pipeline

The quality layer writes a historized `dq_results` table shape in CSV and JSON. A failed control is visible in the output and should route the source to a review queue rather than silently publishing it.
