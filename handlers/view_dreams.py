# handlers/view_dreams.py
# ───────────────────────────────────────────────────────────
import datetime
from typing import List

from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.storage import load_records

from Token import AUTHORIZED_USER_IDS

router = Router()
PAGE = 16  # сколько дат на одной странице


# ─── возвращаем даты с реальными снами ────────────────────
def dates_with_dreams(uid: int) -> List[datetime.date]:
    recs = load_records(uid, "dreams")
    out = []
    skip = (
        "Не запомнил сон",
        "Лень записывать",
        "Помню урывками",
        "",
    )
    for r in recs:
        txt = r.get("dream") or ""
        if txt and not any(txt.startswith(s) for s in skip):
            date_str = r.get("date")
            if not date_str:
                continue
            d = datetime.date.fromisoformat(date_str)
            out.append(d)
    return sorted(set(out))


# ─── клавиатура с пагинацией ──────────────────────────────
def kb_calendar(lst: List[datetime.date], page: int) -> types.InlineKeyboardMarkup:
    start = page * PAGE
    chunk = lst[start:start + PAGE]

    kb = InlineKeyboardBuilder()
    for d in chunk:
        kb.button(text=d.strftime("%d.%m"), callback_data=f"showdream_{d.isoformat()}")

    # навигация
    nav = []
    if page > 0:
        nav.append(("◀", f"dreampg_{page-1}"))
    if start + PAGE < len(lst):
        nav.append(("▶", f"dreampg_{page+1}"))

    kb.adjust(4)
    if nav:
        for txt, cb in nav:
            kb.button(text=txt, callback_data=cb)
        kb.adjust(4, len(nav))
    return kb.as_markup()


# ─── команда /dreams ──────────────────────────────────────
@router.message(Command("dreams"))
async def dreams_root(msg: types.Message):
    if msg.from_user.id not in AUTHORIZED_USER_IDS:
        return
    lst = dates_with_dreams(msg.from_user.id)
    if not lst:
        await msg.reply("Нет сохранённых снов.")
        return
    await msg.reply("Выбери дату:", reply_markup=kb_calendar(lst, 0))


# ─── перелистывание страниц ──────────────────────────────
@router.callback_query(lambda c: c.data.startswith("dreampg_"))
async def change_page(cq: types.CallbackQuery):
    page = int(cq.data.split("_", 1)[1])
    lst = dates_with_dreams(cq.from_user.id)
    await cq.message.edit_reply_markup(reply_markup=kb_calendar(lst, page))
    await cq.answer()


# ─── показ конкретного сна ────────────────────────────────
@router.callback_query(lambda c: c.data.startswith("showdream_"))
async def show_one(cq: types.CallbackQuery, bot: Bot):
    date_iso = cq.data.split("_", 1)[1]
    recs = [r for r in load_records(cq.from_user.id, "dreams") if r.get("date") == date_iso]
    if not recs:
        await cq.answer("Запись не найдена")
        return

    for rec in recs:
        await bot.send_message(
            cq.from_user.id,
            f"🌙 Сон ({date_iso}):\n{rec['dream']}\n\n🌓 {rec['analysis']}"
        )
    await cq.answer()
