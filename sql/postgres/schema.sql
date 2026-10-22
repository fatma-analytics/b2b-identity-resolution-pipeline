CREATE TABLE IF NOT EXISTS raw_signals (signal_id text PRIMARY KEY, source text NOT NULL, email text, phone text, company_name text, domain text, loaded_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS resolved_identities (signal_id text PRIMARY KEY, resolved_person_id text NOT NULL, confidence double precision, source text, resolved_at timestamptz DEFAULT now());
