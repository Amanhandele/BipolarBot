import json,datetime,numpy as np, matplotlib.pyplot as plt
from utils.storage import user_dir
def _series(uid,param):
    folder=user_dir(uid)/'mood'; pts=[]
    if not folder.exists(): return None
    for fp in folder.glob('mood_*.jsonl'):
        date=datetime.datetime.strptime(fp.name.split('_')[1],'%Y%m%d').date()
        with fp.open() as f:
            for line in f:
                d=json.loads(line)
                if param in d and d[param] is not None:
                    pts.append((date.toordinal(), d[param]))
    if not pts: return None
    pts.sort(); return np.array(pts).T
def save_fft(uid,param,out):
    import numpy as np
    res=_series(uid,param); 
    if res is None: return None
    x,y=res
    days=np.arange(x[0],x[-1]+1)
    y=np.interp(days,x,y)-np.mean(y)
    amp=np.abs(np.fft.rfft(y)); freq=np.fft.rfftfreq(len(days),d=1)
    import matplotlib.pyplot as plt
    plt.figure(); plt.plot(freq[1:],amp[1:]); plt.title(f"FFT {param}"); plt.savefig(out); plt.close(); return out
