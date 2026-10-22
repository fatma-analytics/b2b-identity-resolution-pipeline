"""Idempotent local ingestion entry point for the demo."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def ingest():
    source=ROOT/'data/raw/signals_all.csv'; out=ROOT/'data/raw/signals_all.parquet'
    df=pd.read_csv(source); df.to_parquet(out,index=False)
    log=pd.DataFrame([{'source':'signals_all.csv','rows':len(df),'object':str(out),'status':'success'}])
    log.to_csv(ROOT/'data/raw/ingestion_log.csv',index=False)
    return log
if __name__=='__main__': print(ingest().to_string(index=False))
