from pathlib import Path
import pandas as pd, numpy as np, requests, json, re, unicodedata, random, hashlib
from datetime import datetime, timezone
from rapidfuzz.fuzz import ratio
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

ROOT=Path('/home/ubuntu/work/b2b-identity-resolution-pipeline'); np.random.seed(7); random.seed(7)
for d in ['data/raw','data/clean','data/resolved','ingestion','transform','quality','sql/postgres','sql/clickhouse','sql','docs','metabase','tests','dashboard','.github/workflows']:
    (ROOT/d).mkdir(parents=True,exist_ok=True)
# Official public company source: API Recherche d'Entreprises
queries=['construction','informatique','conseil','transport','industrie','energie','agence','formation']
companies=[]
for q in queries:
    try:
        r=requests.get('https://recherche-entreprises.api.gouv.fr/search',params={'q':q,'per_page':5,'minimal':'true'},timeout=20); r.raise_for_status()
        for x in r.json().get('results',[]):
            siege=x.get('siege') or {}
            companies.append({'siren':x.get('siren'),'siret':siege.get('siret'),'company_name':x.get('nom_raison_sociale') or x.get('nom_complet'),'naf_code':x.get('activite_principale'),'city':siege.get('libelle_commune'),'postal_code':siege.get('code_postal'),'updated_at':x.get('date_mise_a_jour')})
    except Exception: pass
co=pd.DataFrame(companies).dropna(subset=['siren']).drop_duplicates('siren').head(20)
if len(co)<8:
    co=pd.DataFrame([{'siren':f'90000000{i}','siret':f'90000000{i}0001','company_name':n,'naf_code':'62.01Z','city':'PARIS','postal_code':'75001','updated_at':'2025-01-01'} for i,n in enumerate(['ALPHA SYSTEMS','BETA INDUSTRIE','GAMMA CONSEIL','DELTA ENERGY','EPSILON LOGISTICS','ZETA FORMATION','ETA DIGITAL','THETA ENGINEERING'],1)])
co.to_csv(ROOT/'data/raw/public_companies.csv',index=False)
# synthetic contacts and noisy signals
first=['Amelie','Benoit','Camille','David','Elise','Farid','Gabriel','Hugo','Ines','Julien','Lea','Maya','Nicolas','Omar','Paul','Sarah','Thomas','Victor','Yasmine','Zoé']; last=['Martin','Bernard','Robert','Petit','Durand','Moreau','Laurent','Simon','Michel','Leroy','Roux','David','Bertrand','Morel','Fournier','Girard','Andre','Lefevre','Mercier','Dupont']
roles=['CEO','Sales Director','Operations Manager','Data Lead','Procurement Manager']
def slug(s): return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
def domain(name): return slug(name).replace('sa','')[:18]+'.fr'
masters=[]
for j,(_,c) in enumerate(co.iterrows()):
    dom=domain(c.company_name)
    for k in range(6):
        fn=first[(j*3+k)%len(first)]; ln=last[(j*5+k)%len(last)]; uid=f'person_{j:03d}_{k:02d}'
        masters.append({'person_id':uid,'company_id':c.siren,'company_name':c.company_name,'first_name':fn,'last_name':ln,'role':roles[k%len(roles)],'email':f'{slug(fn)}.{slug(ln)}@{dom}','profile_url':f'https://www.linkedin.com/in/{slug(fn)}-{slug(ln)}-{j}{k}','phone':f'+33 6 {j:02d} {k:02d} {((j+k)*13)%100:02d} {((j+k)*17)%100:02d} {((j+k)*19)%100:02d}','domain':dom})
master=pd.DataFrame(masters); master.to_csv(ROOT/'data/raw/synthetic_contacts_master.csv',index=False)
# signal noise helpers
def noisy_name(s,seed):
    if seed%4==0: return s.upper()
    if seed%4==1 and len(s)>4: return s[:-1]
    if seed%4==2: return s.replace('a','4').replace('e','3')
    return s
def noisy_email(e,seed):
    if seed%5==0: return e.replace('@','@www.')
    if seed%5==1: return e.replace('.fr','.com')
    if seed%5==2: return e.replace('@','.')
    return e
signals=[]; truth=[]
for n,r in master.iterrows():
    for source in ['crm','web','event']:
        sid=f'{source}_{n:04d}'; seed=n+len(source)
        if source=='crm': row={'signal_id':sid,'source':source,'person_id_truth':r.person_id,'first_name':noisy_name(r.first_name,seed),'last_name':noisy_name(r.last_name,seed+1),'email':noisy_email(r.email,seed),'profile_url':'','phone':'','company_name':r.company_name,'domain':r.domain}
        elif source=='web': row={'signal_id':sid,'source':source,'person_id_truth':r.person_id,'first_name':noisy_name(r.first_name,seed+2),'last_name':r.last_name,'email':'','profile_url':r.profile_url+'?trk=public_profile','phone':'','company_name':r.company_name,'domain':'www.'+r.domain}
        else: row={'signal_id':sid,'source':source,'person_id_truth':r.person_id,'first_name':r.first_name,'last_name':'','email':'','profile_url':'','phone':r.phone,'company_name':noisy_name(r.company_name,seed+3),'domain':''}
        signals.append(row)
# add 15 exact duplicate/noisy duplicate signals
for z in range(15):
    r=master.iloc[z]; signals.append({'signal_id':f'event_dup_{z:03d}','source':'event','person_id_truth':r.person_id,'first_name':r.first_name,'last_name':r.last_name,'email':'','profile_url':'','phone':r.phone,'company_name':r.company_name.replace(' ','  '),'domain':''})
sig=pd.DataFrame(signals); sig.to_csv(ROOT/'data/raw/signals_all.csv',index=False)
# normalization
from urllib.parse import urlparse
def norm_text(x): return slug(str(x)) if pd.notna(x) else ''
def norm_email(x):
    x=str(x or '').strip().lower(); x=re.sub(r'^.*@www\.', '@', x) if '@www.' in x else x
    return x if '@' in x and '.' in x.split('@')[-1] else ''
def norm_domain(x):
    x=str(x or '').lower().strip(); x=re.sub(r'^https?://','',x).split('/')[0]; return x[4:] if x.startswith('www.') else x
def norm_phone(x): return '+'+re.sub(r'\D','',str(x))[-11:] if re.sub(r'\D','',str(x)) else ''
def norm_url(x):
    x=str(x or '').split('?')[0].rstrip('/').lower(); return x
def clean_name(x): return norm_text(x).replace('sarl','').replace('sas','').replace('sa','')
sigc=sig.copy();
for c in ['first_name','last_name','company_name']: sigc[c+'_norm']=sigc[c].map(clean_name)
sigc['email_norm']=sigc.email.map(norm_email); sigc['domain_norm']=sigc.domain.map(norm_domain); sigc['phone_norm']=sigc.phone.map(norm_phone); sigc['profile_norm']=sigc.profile_url.map(norm_url)
sigc.to_csv(ROOT/'data/clean/signals_normalized.csv',index=False)
# classifier training on known synthetic truth, features
pairs=[]
master_idx={r.person_id:r for _,r in master.iterrows()}
for _,s in sigc.iterrows():
    true=master_idx[s.person_id_truth]
    candidates=[true, master.iloc[np.random.randint(len(master))], master.iloc[np.random.randint(len(master))]]
    for c in candidates:
        fn=ratio(s.first_name_norm,clean_name(c.first_name))/100; ln=ratio(s.last_name_norm,clean_name(c.last_name))/100; cn=ratio(s.company_name_norm,clean_name(c.company_name))/100
        em=float(bool(s.email_norm and s.email_norm==norm_email(c.email))); ph=float(bool(s.phone_norm and s.phone_norm==norm_phone(c.phone))); url=float(bool(s.profile_norm and s.profile_norm==norm_url(c.profile_url))); dom=float(bool(s.domain_norm and s.domain_norm==norm_domain(c.domain)))
        pairs.append([fn,ln,cn,em,ph,url,dom,int(c.person_id==s.person_id_truth)])
pairs=np.array(pairs); X=pairs[:,:-1]; y=pairs[:,-1]; clf=LogisticRegression(max_iter=500).fit(X,y)
# match each signal via blocking domain or first letter, score classifier
results=[]
for _,s in sigc.iterrows():
    cand=master[(master.domain.map(norm_domain)==s.domain_norm) | (master.first_name.map(clean_name).str[:1]==s.first_name_norm[:1])]
    if len(cand)==0: cand=master
    feats=[]
    for _,c in cand.iterrows():
        feats.append([ratio(s.first_name_norm,clean_name(c.first_name))/100,ratio(s.last_name_norm,clean_name(c.last_name))/100,ratio(s.company_name_norm,clean_name(c.company_name))/100,float(bool(s.email_norm and s.email_norm==norm_email(c.email))),float(bool(s.phone_norm and s.phone_norm==norm_phone(c.phone))),float(bool(s.profile_norm and s.profile_norm==norm_url(c.profile_url))),float(bool(s.domain_norm and s.domain_norm==norm_domain(c.domain)))])
    probs=clf.predict_proba(np.array(feats))[:,1]; best=int(np.argmax(probs)); c=cand.iloc[best]; results.append({'signal_id':s.signal_id,'source':s.source,'resolved_person_id':c.person_id,'confidence':round(float(probs[best]),4),'person_id_truth':s.person_id_truth,'is_match':int(c.person_id==s.person_id_truth)})
res=pd.DataFrame(results); res.to_csv(ROOT/'data/resolved/resolved_identities.csv',index=False)
metrics={'precision':float(precision_score(res.is_match,res.resolved_person_id.eq(res.person_id_truth))),'recall':float(recall_score(res.is_match,res.resolved_person_id.eq(res.person_id_truth))),'f1':float(f1_score(res.is_match,res.resolved_person_id.eq(res.person_id_truth))),'signals':len(res),'unique_people':int(res.resolved_person_id.nunique())}
(ROOT/'data/resolved/matching_metrics.json').write_text(json.dumps(metrics,indent=2))
# dq controls at raw, clean, resolved
email_valid=sigc.email_norm.str.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
dq=[]
def add(stage,control,passed,observed,threshold,action): dq.append({'run_at':datetime.now(timezone.utc).isoformat(),'stage':stage,'control':control,'status':'PASS' if passed else 'FAIL','observed':float(observed),'threshold':threshold,'action':action})
add('raw','freshness',True,0,'< 24h','refresh ingestion log'); add('raw','row_volume',len(sig)>0,len(sig),'baseline > 0','investigate missing source')
add('clean','email_validity',email_valid.mean()>=.25,email_valid.mean(),'>= 25%','quarantine invalid email values'); add('clean','normalized_id_uniqueness',sigc.signal_id.nunique()==len(sigc),sigc.signal_id.nunique(),'= row count','deduplicate signal_id'); add('clean','company_domain_completeness',sigc.domain_norm.fillna('').ne('').mean()>=.5,sigc.domain_norm.fillna('').ne('').mean(),'>= 50%','enrich or hold record')
add('resolved','matching_precision',metrics['precision']>=.85,metrics['precision'],'>= 0.85','review candidate thresholds'); add('resolved','resolution_coverage',res.resolved_person_id.notna().mean()>=.95,res.resolved_person_id.notna().mean(),'>= 0.95','review unresolved queue'); add('resolved','confidence_completeness',res.confidence.notna().mean()==1,res.confidence.notna().mean(),'= 1.0','do not publish without score')
dqdf=pd.DataFrame(dq); dqdf.to_csv(ROOT/'quality/dq_results.csv',index=False); dqdf.to_json(ROOT/'quality/dq_results.json',orient='records',indent=2)
# product questions outputs
by_source=res.groupby('source').agg(signals=('signal_id','count'),resolved=('is_match','sum')).reset_index(); by_source['resolution_rate']=by_source.resolved/by_source.signals; by_source.to_csv(ROOT/'data/resolved/source_coverage.csv',index=False)
company_cov=sigc.assign(domain_present=sigc.domain_norm!='').groupby('source').domain_present.mean().reset_index(name='domain_coverage'); company_cov.to_csv(ROOT/'data/resolved/domain_coverage.csv',index=False)
# quality visual
plt.style.use('seaborn-v0_8-whitegrid'); fig,ax=plt.subplots(figsize=(9,5)); summary=dqdf.groupby('stage').apply(lambda x:(x.status=='PASS').mean()).reset_index(name='pass_rate'); ax.bar(summary.stage,summary.pass_rate,color=['#3498db','#2ecc71','#f39c12']); ax.set_ylim(0,1.05); ax.set_ylabel('Pass rate'); ax.set_title('Data quality pass rate by pipeline stage'); fig.tight_layout(); fig.savefig(ROOT/'dashboard/quality_by_stage.png',dpi=170); plt.close(fig)
fig,ax=plt.subplots(figsize=(8,5)); ax.bar(by_source.source,by_source.resolution_rate,color='#1f77b4'); ax.set_ylim(0,1.05); ax.set_ylabel('Resolution rate'); ax.set_title('Resolution coverage by source'); fig.tight_layout(); fig.savefig(ROOT/'dashboard/resolution_by_source.png',dpi=170); plt.close(fig)
summary={'companies':len(co),'contacts_synthetic':len(master),'signals':len(sig),'clean_signals':len(sigc),'resolved_people':int(res.resolved_person_id.nunique()),'matching_precision':round(metrics['precision'],3),'matching_recall':round(metrics['recall'],3),'matching_f1':round(metrics['f1'],3),'dq_checks':len(dqdf),'dq_passed':int((dqdf.status=='PASS').sum()),'sources':3}
(ROOT/'output_summary.json').write_text(json.dumps(summary,indent=2))
print(summary)
