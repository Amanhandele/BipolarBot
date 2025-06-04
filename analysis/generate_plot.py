import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional
from math import ceil

from utils.storage import load_records


def _load(uid: int) -> pd.DataFrame:
    """Return DataFrame with mood records and dream metrics."""
    rows: list[dict] = []
    for rec in load_records(uid, "mood"):
        date_str = rec.get("date")
        if not date_str:
            continue
        try:
            rec_date = datetime.date.fromisoformat(str(date_str))
        except ValueError:
            try:
                rec_date = datetime.datetime.strptime(str(date_str)[:8], "%Y%m%d").date()
            except ValueError:
                continue
        rec["date"] = rec_date
        rows.append(rec)
    df = pd.DataFrame(rows)

    # добавляем показатели снов
    dream_rows = []
    for rec in load_records(uid, "dreams"):
        date = rec.get("date")
        metrics = rec.get("metrics") or {}
        if not date or not metrics:
            continue
        row = {"date": pd.to_datetime(date)}
        if "cim_score" in metrics:
            row["cim_score"] = metrics["cim_score"]
        if "intensity" in metrics:
            row["intensity"] = metrics["intensity"]
        if "emotions" in metrics:
            for emo in metrics["emotions"]:
                row.setdefault(f"emo_{emo}", metrics.get("intensity", 1))
        dream_rows.append(row)

    df_dream = pd.DataFrame(dream_rows)
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    if not df_dream.empty:
        df = pd.concat([df, df_dream], ignore_index=True, sort=False)
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


def emotion_counts(uid: int) -> dict[str, int]:
    """Return a mapping emotion -> total occurrences in dreams."""
    counts: dict[str, int] = {}
    for rec in load_records(uid, "dreams"):
        metrics = rec.get("metrics") or {}
        for emo in metrics.get("emotions", []):
            counts[emo] = counts.get(emo, 0) + 1
    return counts


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

    df = df.sort_values("date")
    df.set_index("date", inplace=True)

    daily_mean = df[params].resample("1D").mean().fillna(0)
    if daily_mean.empty:
        return None

    if len(params) > 1:
        mean = daily_mean.rolling(window=7, min_periods=1).mean()
    else:
        step = 1
        if len(daily_mean) > 60:
            span = (daily_mean.index[-1] - daily_mean.index[0]).days + 1
            step = max(1, ceil(span / 60))
        mean = daily_mean.resample(f"{step}D").mean()

    plt.figure()
    for p in params:
        if p in mean.columns:
            series = mean[p]
            if len(params) > 1:
                plt.plot(series.index, series, label=p)
            else:
                plt.plot(series.index, series, label=p)

    # ───── оформление оси X ────────────────────────────────
    months_nom = [
        "январь", "февраль", "март", "апрель", "май", "июнь",
        "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
    ]
    months_gen = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]

    dates = mean.index.to_pydatetime()
    labels = []
    ticks = []

    if period == "week":
        ticks = dates
        labels = [f"{d.day} {months_gen[d.month-1]}" for d in dates]
        start = dates[0].date(); end = dates[-1].date()
        if start.year == end.year:
            if start.month == end.month:
                xlabel = f"{months_nom[start.month-1]} {start.year}"
            else:
                xlabel = f"{months_nom[start.month-1]}-{months_nom[end.month-1]} {start.year}"
        else:
            xlabel = (
                f"{months_nom[start.month-1]} {start.year}-"
                f"{months_nom[end.month-1]} {end.year}"
            )

    elif period == "month":
        step = max(1, len(dates) // 6)
        ticks = dates[::step]
        labels = [f"{d.day} {months_gen[d.month-1]}" for d in ticks]
        start = dates[0].date(); end = dates[-1].date()
        if start.month == end.month and start.year == end.year:
            xlabel = f"{months_nom[start.month-1]} {start.year}"
        else:
            if start.year == end.year:
                xlabel = f"{months_nom[start.month-1]}-{months_nom[end.month-1]} {start.year}"
            else:
                xlabel = (
                    f"{months_nom[start.month-1]} {start.year}-"
                    f"{months_nom[end.month-1]} {end.year}"
                )

    elif period == "year":
        # первые числа месяцев
        start = dates[0].replace(day=1)
        end_dt = dates[-1].replace(day=1)
        months_range = pd.date_range(start=start, end=end_dt, freq="MS")
        ticks = months_range.to_pydatetime()
        labels = [months_nom[d.month-1] for d in ticks]
        y1 = ticks[0].year
        y2 = ticks[-1].year
        xlabel = f"{y1} год" if y1 == y2 else f"{y1}-{y2} годы"

    else:  # period == "all"
        start = dates[0]
        end = dates[-1]
        months_range = pd.date_range(start=start.replace(day=1), end=end, freq="MS")
        step = max(1, len(months_range) // 6)
        ticks = months_range[::step].to_pydatetime()
        labels = [f"{months_nom[d.month-1]} {str(d.year % 100).zfill(2)}" for d in ticks]
        xlabel = (
            f"{months_nom[start.month-1]} {start.year} - "
            f"{months_nom[end.month-1]} {end.year}"
        )

    plt.xticks(ticks, labels, rotation=45, ha="right")
    plt.xlabel(xlabel)

    plt.legend()
    plt.title(f"{', '.join(params)} ({period})")
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    return out
