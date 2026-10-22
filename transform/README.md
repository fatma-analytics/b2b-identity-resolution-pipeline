# Transformation

Normalization lowercases emails, removes `www.` from domains, strips URL query parameters, produces a compact phone representation, and removes legal-form tokens from company names. Blocking uses domain or first-name initial. Matching combines exact email/profile/phone evidence, RapidFuzz similarities and a logistic-regression classifier trained on synthetic truth pairs.
