# handlers/dreams.py
# ───────────────────────────────────────────────────────────
import asyncio, datetime, json, re
from openai import AsyncOpenAI
from typing import Optional
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from Token import AUTHORIZED_USER_IDS
from utils.storage import save_json
from utils import send_long

router = Router()


def _fmt_metrics(metrics: dict) -> str:
    """Return formatted metrics block for Telegram."""

    if not metrics:
        return ""

    lines = ["<b>Метрики сна</b>"]

    if metrics.get("intensity") is not None:
        lines.append(f"Интенсивность: {metrics['intensity']}")

    emotions = metrics.get("emotions") or []
    if emotions:
        lines.append("Распознанные эмоции:")
        lines.extend(emotions)

    return "\n\n" + "\n".join(lines)


# user_id → {"msgs": list[str], "btn": int, "task": asyncio.Task, "date": str}
_active: dict[int, dict] = {}
_prompt_dates: dict[int, str] = {}
TIMEOUT = 900  # 15 минут

# ───── учёт времени запроса ─────────────────────────────────
def register_prompt(uid: int, date_iso: Optional[str] = None) -> None:
    """Remember when the bot asked to record a dream."""
    if date_iso is None:
        date_iso = datetime.date.today().isoformat()
    _prompt_dates[uid] = date_iso


# ───── клавиатура ──────────────────────────────────────────
def dream_kb() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Записать сон", callback_data="dream_write")
    kb.button(text="Не запомнил",      callback_data="dream_none")
    kb.button(text="Лень записывать",  callback_data="dream_lazy")
    kb.button(text="Помню урывками",   callback_data="dream_frag")
    kb.adjust(1)
    return kb.as_markup()


async def _timeout(uid: int, bot: Bot):
    await asyncio.sleep(TIMEOUT)
    if uid in _active:
        await _finish(uid, bot)


async def start_record(bot: Bot, uid: int, date_iso: Optional[str] = None):
    if date_iso is None:
        date_iso = _prompt_dates.pop(uid, datetime.date.today().isoformat())
    kb = InlineKeyboardBuilder()
    kb.button(text="🏁 Закончить запись", callback_data="dream_end")
    msg = await bot.send_message(uid, "Записываю сон…", reply_markup=kb.as_markup())
    task = asyncio.create_task(_timeout(uid, bot))
    _active[uid] = {"msgs": [], "btn": msg.message_id, "task": task, "date": date_iso}


async def _finish(uid: int, bot: Bot):
    info = _active.pop(uid, None)
    if not info:
        return
    if info["task"]:
        info["task"].cancel()
    try:
        await bot.delete_message(uid, info["btn"])
    except Exception:
        pass
    text = "\n".join(info["msgs"]).strip()
    if text:
        analysis, metrics = await _commit(uid, text, info["date"])
        await send_long(
            bot,
            uid,
            f"🌓 Анализ сна:\n{analysis}{_fmt_metrics(metrics)}",
        )
        from handlers.manage import main_kb
        await bot.send_message(uid, "Меню:", reply_markup=main_kb())
    else:
        payload = {"dream": "", "analysis": "", "metrics": {}, "date": info["date"]}
        save_json(uid, "dreams", "dream", payload)
        await bot.send_message(uid, "Сон сохранён (пусто).")
        from handlers.manage import main_kb
        await bot.send_message(uid, "Меню:", reply_markup=main_kb())


# ───── GPT-анализ ──────────────────────────────────────────
async def analyze(text: str) -> str:
    """Return GPT analysis with metrics line."""
    try:
        from Token import OPENAI_API_KEY
        if not OPENAI_API_KEY:
            raise Exception("Фича с анализом снов через чатгпт пока не работает.")
        from config import CIM_EMOTIONS

        emotions = ", ".join(CIM_EMOTIONS)
        prompt = (
            "Сначала подробно проанализируй сон по Юнгу без форматирования Markdown, с форматированием для Telegram."
            "В конце ответа отдельной строкой напиши 'METRICS: '{\"intensity\": <0.5-3>, \"emotions\":[...]}'."
            "Для расчёта CIM-анализа перечисли эмоции только из списка: "
            f"{emotions}. "
        )

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o",

            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            max_tokens=3500,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(ошибка OpenAI: {e})"


async def _commit(uid: int, dream_txt: str, date_iso: Optional[str] = None):
    metrics = {}
    analysis = ""
    raw = ""
    if dream_txt.strip():
        raw = await analyze(dream_txt)
        analysis = raw
        m = re.search(r"METRICS:\s*(['\"])?(\{.*\})(?:\1)?", raw, re.S)
        if m:
            json_str = m.group(2)

            try:
                metrics = json.loads(json_str)
            except Exception:
                metrics = {}
            analysis = raw[: m.start()].strip()
        else:
            analysis = re.sub(r"METRICS:.*", "", raw, flags=re.S).strip()

    intensity = metrics.get("intensity")
    emotions = metrics.get("emotions") or []
    if intensity and emotions:
        from config import EMOTION_COEFF
        coeffs = [EMOTION_COEFF.get(e.lower(), 0) for e in emotions]
        if coeffs:
            e_val = sum(coeffs) / len(coeffs)
            metrics["cim_score"] = round(float(intensity) * e_val, 2)

    if not date_iso:
        date_iso = datetime.date.today().isoformat()
    payload = {
        "dream": dream_txt,
        "analysis": analysis,
        "metrics": metrics,
        "date": date_iso,
    }
    save_json(uid, "dreams", "dream", payload)
    return analysis, metrics


# ───── команды /dream и кнопки ─────────────────────────────
@router.message(Command("dream"))
async def cmd_dream(msg: types.Message):
    if msg.from_user.id not in AUTHORIZED_USER_IDS:
        return
    text = msg.text.replace("/dream", "", 1).strip()
    if text:
        analysis, metrics = await _commit(msg.from_user.id, text, None)
        await send_long(
            msg.bot,
            msg.chat.id,
            f"🌓 Анализ сна:\n{analysis}{_fmt_metrics(metrics)}",
            reply_to_message_id=msg.message_id,
        )
        from handlers.manage import main_kb
        await msg.answer("Меню:", reply_markup=main_kb())
    else:
        await msg.reply("Отправь текст сна сообщением или выбери кнопку:", reply_markup=dream_kb())
        await start_record(msg.bot, msg.from_user.id)


# Обрабатываем кнопки, кроме завершения записи
@router.callback_query(lambda c: c.data.startswith("dream_") and c.data != "dream_end")
async def dream_buttons(cq: types.CallbackQuery, bot: Bot):
    uid = cq.from_user.id
    if uid not in AUTHORIZED_USER_IDS:
        await cq.answer(); return

    code = cq.data
    if code == "dream_write":
        await start_record(bot, uid)
        await cq.message.edit_text("Жду текст сна…")
        await cq.answer()
        return

    label_map = {
        "dream_none": "Не запомнил сон",
        "dream_lazy": "Лень записывать",
        "dream_frag": "Помню урывками",
    }
    label = label_map.get(code, code)
    info = _active.pop(uid, None)
    if info:
        date_iso = info.get("date")
    else:
        date_iso = _prompt_dates.pop(uid, datetime.date.today().isoformat())
    payload = {"dream": label, "analysis": "(нет)", "metrics": {}, "date": date_iso}
    save_json(uid, "dreams", "dream", payload)
    await cq.message.edit_text(f"📑 Записал: {label}")
    from handlers.manage import main_kb
    await cq.message.answer("Меню:", reply_markup=main_kb())
    await cq.answer()


# ───── фиксация сообщений во время записи сна ──────────────
@router.message(lambda m: m.from_user.id in _active)
async def collect_dream(msg: types.Message):
    info = _active.get(msg.from_user.id)
    if not info:
        return
    info["msgs"].append(msg.text)
    if info["task"]:
        info["task"].cancel()
    try:
        await msg.bot.delete_message(msg.chat.id, info["btn"])
    except Exception:
        pass
    kb = InlineKeyboardBuilder()
    kb.button(text="🏁 Закончить запись", callback_data="dream_end")
    new = await msg.answer("Записываю сон…", reply_markup=kb.as_markup())
    info["btn"] = new.message_id
    info["task"] = asyncio.create_task(_timeout(msg.from_user.id, msg.bot))


@router.callback_query(lambda c: c.data == "dream_end")
async def end_dream(cq: types.CallbackQuery, bot: Bot):
    await _finish(cq.from_user.id, bot)
    await cq.answer()
