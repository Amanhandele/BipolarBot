# utils/storage.py
# ───────────────────────────────────────────────────────────
import datetime, json, os
from pathlib import Path
from typing import Any, Dict, List

from config import BASE_DIR
from utils.crypto import encrypt, decrypt
from handlers.auth import get_pass

# ───────────────────────────────────────────────────────────
def user_dir(uid: int) -> Path:
    p = BASE_DIR / str(uid)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─────────────── запись одной строки JSONL ────────────────
def save_jsonl(uid: int, sub: str, prefix: str, data: Dict[str, Any]) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = user_dir(uid) / sub
    folder.mkdir(exist_ok=True)

    pwd = get_pass(uid)
    payload = {"enc": encrypt(data, pwd)} if pwd else data

    fp = folder / f"{prefix}_{ts}.jsonl"
    with fp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return fp


# ─────────── чтение всех строк с защитой от «кривых» ───────
def load_records(uid: int, sub: str) -> List[Dict[str, Any]]:
    """
    Возвращает список словарей (уже расшифрованных, если пароль в RAM).
    Строки, которые не декодируются как UTF-8 или не парсятся в JSON,
    просто пропускаются, чтобы не ронять бота.
    """
    folder = user_dir(uid) / sub
    if not folder.exists():
        return []

    pwd = get_pass(uid)
    out: List[Dict[str, Any]] = []

    for fp in sorted(folder.glob(f"{sub[:-1]}_*")):
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
                    if not pwd:
                        continue                 # нет пароля → пропуск
                    j = decrypt(j["enc"], pwd) or {}
                out.append(j)
    return out
