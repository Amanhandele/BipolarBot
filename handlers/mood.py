# handlers/mood.py
# ─────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, Optional

from aiogram import Router, Bot, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import PARAMETERS
from Token import AUTHORIZED_USER_IDS
from utils.storage import user_dir, save_json

router = Router()
_state: Dict[int, Dict] = {}          # user_id → {"index": int, "data": dict, "file": Path}


# ─────────────────────────────────────────────────────────
def build_kb(param: str) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for v in range(-3, 4):                          # -3 … 3
        kb.button(text=str(v), callback_data=f"m_{param}_{v}")
    kb.button(text="¯\\_(ツ)_/¯", callback_data=f"m_{param}_x")
    kb.adjust(7)
    return kb.as_markup()


async def start(bot: Bot, uid: int, backdate: Optional[str] = None) -> None:
    _state[uid] = {"index": 0, "data": {"date": backdate}, "file": None}
    k, label = PARAMETERS[0]
    await bot.send_message(uid, f"{label}  (-3…3):", reply_markup=build_kb(k))


# ─────────────────────────────────────────────────────────
@router.message(Command("checkin"))
async def cmd_checkin(msg: types.Message):
    if msg.from_user.id not in AUTHORIZED_USER_IDS:
        return
    await start(msg.bot, msg.from_user.id)
    await msg.reply("Быстрый чек-ин запущен.")


# ─────────────────────────────────────────────────────────
@router.callback_query(lambda c: c.data.startswith("m_"))
async def cb_scale(cq: types.CallbackQuery):
    payload, val = cq.data.rsplit("_", 1)          # m_<param>_<val>
    _, param = payload.split("_", 1)

    st = _state.setdefault(cq.from_user.id, {"index": 0, "data": {}, "file": None})
    st["data"][param] = None if val == "x" else int(val)
    st["index"] += 1

    if st["index"] >= len(PARAMETERS):
        # Все ответы получены — спрашиваем summary, сохранять пока рано
        await cq.message.answer(
            "📝 Что было самым живым сегодня? (можно ничего не писать)"
        )
        # запускаем тайм-аут ожидания текста
        asyncio.create_task(_summary_timeout(cq.from_user.id))
        await cq.answer()
        return

    nxt_key, nxt_label = PARAMETERS[st["index"]]
    await cq.message.answer(f"{nxt_label}  (-3…3):", reply_markup=build_kb(nxt_key))
    await cq.answer()


# ─────────────────────────────────────────────────────────
async def _save_final(uid: int):
    """Создаём/перезаписываем единственный файл итогов."""
    st = _state.get(uid)
    if st is None:
        return

    # Если файла ещё нет — создаём, иначе перезаписываем
    if st["file"] is None:
        fp = save_json(uid, "mood", "mood", st["data"])
        st["file"] = fp
    else:
        Path(st["file"]).write_text(
            json.dumps(st["data"], ensure_ascii=False) + "\n",
            encoding="utf-8",
        )  # простая перезапись JSONL одной строкой


async def _summary_timeout(uid: int, delay: int = 600):
    """Через delay секунд, если summary не пришёл, дописываем (пусто)."""
    await asyncio.sleep(delay)
    st = _state.get(uid)
    if st is None or "summary" in st["data"]:
        return                            # текст пришёл, ничего делать не нужно
    st["data"]["summary"] = "(пусто)"
    await _save_final(uid)
    _state.pop(uid, None)


# ─────────────────────────────────────────────────────────
@router.message(lambda m: m.from_user.id in AUTHORIZED_USER_IDS)
async def summary_or_plain(msg: types.Message):
    st = _state.get(msg.from_user.id)
    if st is None or st["index"] < len(PARAMETERS):
        return     # нет открытой сессии или чек-ин ещё не закончен

    st["data"]["summary"] = msg.text or "(пусто)"
    await _save_final(msg.from_user.id)
    _state.pop(msg.from_user.id, None)
    await msg.reply("✅ Сохранено!")
    from handlers.manage import main_kb
    await msg.answer("Меню:", reply_markup=main_kb())
