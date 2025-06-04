import json
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional

from utils.storage import user_dir
from utils.crypto import decrypt
from handlers.auth import get_pass


def _load(uid: int) -> pd.DataFrame:
    """Return DataFrame with decrypted mood records."""
    folder = user_dir(uid) / "mood"
    rows: list[dict] = []
    if not folder.exists():
        return pd.DataFrame()

    pwd = get_pass(uid)
    for fp in sorted(folder.glob("mood_*.jsonl")):
        date = datetime.datetime.strptime(fp.name.split("_")[1], "%Y%m%d").date()
        with fp.open("rb") as f:
            for raw in f:
                try:
                    line = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "enc" in d:
                    if not pwd:
                        continue
                    d = decrypt(d["enc"], pwd) or {}
                d.setdefault("date", date)
                rows.append(d)

    df = pd.DataFrame(rows)
    if not df.empty and "date" in df.columns:
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


def plot_multi(uid: int, params: list[str], period: str, out: str, page: int = 0) -> Optional[str]:

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
