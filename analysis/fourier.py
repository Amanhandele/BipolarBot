import datetime
import numpy as np
import matplotlib.pyplot as plt

from analysis.generate_plot import _load


def _series(uid: int, param: str):
    df = _load(uid)
    if df.empty or param not in df.columns:
        return None
    df = df.dropna(subset=[param]).sort_values("date")
    if df.empty:
        return None
    x = df["date"].dt.date.map(datetime.date.toordinal).to_numpy()
    y = df[param].to_numpy()
    return np.array([x, y])
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
