# utils/storage.py
# ───────────────────────────────────────────────────────────
import datetime, json
from pathlib import Path
from typing import Any, Dict, List

from config import BASE_DIR

# ───────────────────────────────────────────────────────────
def user_dir(uid: int) -> Path:
    p = BASE_DIR / str(uid)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─────────────── запись отдельного JSON-файла ──────────────
def save_json(uid: int, sub: str, prefix: str, data: Dict[str, Any]) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = user_dir(uid) / sub
    folder.mkdir(exist_ok=True)

    fp = folder / f"{prefix}_{ts}.json"
    fp.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    return fp


# ─────────────── запись в указанный JSON-файл ───────────────
def save_json_named(uid: int, sub: str, name: str, data: Dict[str, Any]) -> Path:
    """Write JSON data to a file with an explicit name."""
    folder = user_dir(uid) / sub
    folder.mkdir(exist_ok=True)

    if not name.endswith(".json"):
        name += ".json"

    fp = folder / name
    fp.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    return fp


# ─────────── чтение всех строк с защитой от «кривых» ───────
def load_records(uid: int, sub: str) -> List[Dict[str, Any]]:
    """
    Возвращает список словарей. Строки, которые не декодируются как UTF-8
    или не парсятся в JSON, просто пропускаются, чтобы не ронять бота.
    Старые зашифрованные записи игнорируются.
    """
    folder = user_dir(uid) / sub
    if not folder.exists():
        return []

    out: List[Dict[str, Any]] = []

    prefix = sub[:-1] if sub.endswith("s") else sub
    for fp in sorted(folder.glob(f"{prefix}_*")):
        with fp.open("rb") as f:                 # ← бинарный режим
            for raw in f:
                try:
                    line = raw.decode("utf-8")   # плохие байты → UnicodeError
                except UnicodeDecodeError:
                    continue                     # пропускаем старую строку
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue                     # тоже пропускаем

                if "enc" in j:
                    continue  # старые зашифрованные записи пропускаем
                out.append(j)
    return out
