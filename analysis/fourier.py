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
def save_fft(uid: int, param: str, out: str):
    res = _series(uid, param)
    if res is None:
        return None

    x, y = res
    days = np.arange(x[0], x[-1] + 1)
    y = np.interp(days, x, y) - np.mean(y)

    amp = np.abs(np.fft.rfft(y))
    freq = np.fft.rfftfreq(len(days), d=1)

    plt.figure()
    plt.plot(freq[1:], amp[1:])
    plt.title(f"FFT {param}")

    if len(amp) > 4:
        idx = np.argsort(amp[1:])[-3:][::-1]
        for i in idx:
            f = freq[1:][i]
            if f == 0:
                continue
            T = 1 / f
            if T <= 90:
                label = f"{round(T)} дн"
            elif T <= 365 * 3:
                label = f"{round(T/30)} мес"
            else:
                label = f"{round(T/365, 1)} лет"
            plt.plot(f, amp[1:][i], "ro")
            plt.text(f, amp[1:][i], label)

    plt.savefig(out)
    plt.close()
    return out
