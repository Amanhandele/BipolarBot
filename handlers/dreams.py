# handlers/dreams.py
# ───────────────────────────────────────────────────────────
import asyncio, datetime, openai
from typing import Optional
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from Token import AUTHORIZED_USER_IDS
from utils.storage import save_jsonl

router = Router()


# user_id → date (None = сегодня)
_waiting: dict[int, str] = {}


# ───── клавиатура ──────────────────────────────────────────
def dream_kb() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Записать сон", callback_data="dream_write")
    kb.button(text="Не запомнил",      callback_data="dream_none")
    kb.button(text="Лень записывать",  callback_data="dream_lazy")
    kb.button(text="Помню урывками",   callback_data="dream_frag")
    kb.adjust(1)
    return kb.as_markup()


# ───── GPT-анализ ──────────────────────────────────────────
async def analyze(text: str) -> str:
    try:
        from Token import OPENAI_API_KEY
        openai.api_key = OPENAI_API_KEY
        if not OPENAI_API_KEY:
            raise Exception("Фича с анализом снов через чатгпт пока не работает.")
        resp = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Проанализируй нижеследующий сон по Юнгу."},
                {"role": "user",   "content": text}
            ],
            max_tokens=3500,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(ошибка OpenAI: {e})"


async def _commit(uid: int, dream_txt: str, date_iso: Optional[str] = None):
    analysis = await analyze(dream_txt)
    if not date_iso:
        date_iso = datetime.date.today().isoformat()
    payload = {"dream": dream_txt, "analysis": analysis, "date": date_iso}
    save_jsonl(uid, "dreams", "dream", payload)
    return analysis


# ───── команды /dream и кнопки ─────────────────────────────
@router.message(Command("dream"))
async def cmd_dream(msg: types.Message):
    if msg.from_user.id not in AUTHORIZED_USER_IDS:
        return
    text = msg.text.replace("/dream", "", 1).strip()
    if text:
        analysis = await _commit(msg.from_user.id, text, None)
        await msg.reply(f"🌓 Анализ сна:\n{analysis}")
    else:
        # ставим флаг ожидания текста
        _waiting[msg.from_user.id] = None
        await msg.reply("Отправь текст сна сообщением или выбери кнопку:", reply_markup=dream_kb())


@router.callback_query(lambda c: c.data.startswith("dream_"))
async def dream_buttons(cq: types.CallbackQuery):
    uid = cq.from_user.id
    if uid not in AUTHORIZED_USER_IDS:
        await cq.answer(); return

    code = cq.data
    if code == "dream_write":
        _waiting[uid] = None          # ждём текст
        await cq.message.edit_text("Жду текст сна…")
        await cq.answer()
        return

    label_map = {
        "dream_none": "Не запомнил сон",
        "dream_lazy": "Лень записывать",
        "dream_frag": "Помню урывками",
    }
    label = label_map.get(code, code)
    save_jsonl(uid, "dreams", "dream", {"dream": label, "analysis": "(нет)"})
    _waiting.pop(uid, None)
    await cq.message.edit_text(f"📑 Записал: {label}")
    await cq.answer()


# ───── перехватываем первое сообщение, когда ждём сон ─────
@router.message(lambda m: m.from_user.id in _waiting)
async def catch_dream(msg: types.Message):
    uid = msg.from_user.id
    date_iso = _waiting.pop(uid)
    analysis = await _commit(uid, msg.text, date_iso)
    await msg.reply(f"🌓 Анализ сна:\n{analysis}")