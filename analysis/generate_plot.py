import json
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib.pyplot as plt

from utils.storage import user_dir


def _load(uid: int) -> pd.DataFrame:
    folder = user_dir(uid) / "mood"
    rows = []
    if not folder.exists():
        return pd.DataFrame()
    for fp in folder.glob("mood_*.jsonl"):
        date = datetime.datetime.strptime(fp.name.split("_")[1], "%Y%m%d").date()
        with fp.open() as f:
            for line in f:
                d = json.loads(line)
                d["date"] = date
                rows.append(d)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def _slice(df: pd.DataFrame, period: str, page: int) -> pd.DataFrame:
    if period == "all" or df.empty:
        return df
    last = df["date"].max()
    if period == "year":
        start = (last - relativedelta(years=page)).replace(month=1, day=1)
        end = start + relativedelta(years=1)
    elif period == "month":
        start = (last.replace(day=1) - relativedelta(months=page))
        end = start + relativedelta(months=1)
    elif period == "week":
        start = last - datetime.timedelta(days=last.weekday()) - datetime.timedelta(weeks=page)
        end = start + datetime.timedelta(weeks=1)
    else:
        return df
    return df[(df["date"] >= start) & (df["date"] < end)]


def plot_multi(uid: int, params: list[str], period: str, out: str, page: int = 0) -> str | None:
    df = _load(uid)
    if df.empty:
        return None
    params = [p for p in params if p in df.columns]
    if not params:
        return None
    df = _slice(df, period, page)
    if df.empty:
        return None
    grp = df.groupby("date")[params].mean()
    if grp.empty:
        return None
    plt.figure()
    for p in params:
        if p in grp.columns:
            plt.plot(grp.index, grp[p], "-o", label=p)
    plt.legend()
    plt.title(f"{', '.join(params)} ({period})")
    plt.savefig(out)
    plt.close()
    return out
