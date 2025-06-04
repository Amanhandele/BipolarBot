import json,datetime,pandas as pd, matplotlib.pyplot as plt
from utils.storage import user_dir
def _load(uid):
    folder=user_dir(uid)/'mood'; rows=[]
    if not folder.exists(): return pd.DataFrame()
    for fp in folder.glob('mood_*.jsonl'):
        date=datetime.datetime.strptime(fp.name.split('_')[1],'%Y%m%d').date()
        with fp.open() as f:
            for line in f: d=json.loads(line); d['date']=date; rows.append(d)
    return pd.DataFrame(rows)
def plot(uid,param,period,out):
    df=_load(uid)
    if df.empty or param not in df.columns: return None
    if period=='days':
        start=df['date'].max()-datetime.timedelta(days=30)
        df=df[df['date']>=start]; grp=df.groupby('date')[param]
    elif period=='weeks':
        df['week']=df['date'].apply(lambda d:d.isocalendar()[1]); grp=df.groupby('week')[param]
    else:
        df['month']=df['date'].apply(lambda d:d.replace(day=1)); grp=df.groupby('month')[param]
    mean,std=grp.mean(),grp.std().fillna(0)
    plt.figure(); plt.errorbar(mean.index, mean.values, yerr=std.values, fmt='-o'); plt.title(f"{param} ({period})"); plt.savefig(out); plt.close(); return out
