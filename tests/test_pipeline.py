import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def test_outputs_exist():
    assert (ROOT/'data/resolved/resolved_identities.csv').exists()
    assert (ROOT/'quality/dq_results.json').exists()
def test_signal_keys_unique():
    df=pd.read_csv(ROOT/'data/clean/signals_normalized.csv')
    assert df.signal_id.is_unique
def test_matching_metrics():
    m=json.loads((ROOT/'data/resolved/matching_metrics.json').read_text())
    assert m['f1'] >= 0.85
