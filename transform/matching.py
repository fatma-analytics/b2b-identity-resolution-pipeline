"""Blocking and fuzzy feature helpers used by the generated pipeline."""
from rapidfuzz.fuzz import ratio
def fuzzy_features(signal, candidate):
    return {'first_name_similarity':ratio(signal.get('first_name_norm',''),candidate.get('first_name_norm',''))/100,'last_name_similarity':ratio(signal.get('last_name_norm',''),candidate.get('last_name_norm',''))/100,'company_similarity':ratio(signal.get('company_name_norm',''),candidate.get('company_name_norm',''))/100}
def block_keys(signal):
    return {('domain',signal.get('domain_norm','')),('first_initial',signal.get('first_name_norm','')[:1])}
