"""Reusable normalization helpers."""
import re, unicodedata
def normalize_text(value):
    value=unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',value)
def normalize_domain(value):
    value=str(value or '').lower().strip(); value=re.sub(r'^https?://','',value).split('/')[0]
    return value[4:] if value.startswith('www.') else value
def normalize_phone(value):
    digits=re.sub(r'\D','',str(value or '')); return '+'+digits[-11:] if digits else ''
