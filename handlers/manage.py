# handlers/manage.py
# ───────────────────────────────────────────────────────────
import re, datetime
from aiogram import Router, types, Bot
from aiogram.types import FSInputFile
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers import view_dreams
from utils.env import AUTHORIZED_USER_IDS
from config import PARAMETERS, GRAPH_PARAMS, CIM_EMOTIONS, load_user_times, save_user_times
from analysis.generate_plot import plot_multi
from analysis.fourier import save_fft
from utils.storage import user_dir
from analysis.export import export
from handlers import mood
from handlers import view_dreams   # 📚 кнопка сны
from handlers import missed
from handlers import auth
from dataclasses import dataclass, field
from aiogram.exceptions import TelegramBadRequest

from typing import Optional


@dataclass
class GraphState:
    period: str = "all"
    page: int = 0
    params: list[str] = field(default_factory=list)

    msg_id: Optional[int] = None


_graph_state: dict[int, GraphState] = {}
_cim_state: dict[int, GraphState] = {}


router = Router()


async def _edit(message: types.Message, text: str, markup: types.InlineKeyboardMarkup):
    """Edit message text or caption depending on content type."""
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "no text" in str(e).lower():
            await message.edit_caption(text, reply_markup=markup)
        elif "message is not modified" not in str(e).lower():
            raise

# ───── главное меню ───────────────────────────────────────
# ───────── главное меню ───────────────────────────────────
def main_kb() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 График",        callback_data="mg_graph")
    kb.button(text="🔍 FFT",           callback_data="mg_fft")
    kb.button(text="📚 Сны",           callback_data="mg_dreams")
    kb.button(text="🎭 CIM-анализ",   callback_data="mg_cim")
    kb.button(text="🗓 Пропуски",      callback_data="mg_missed")
    kb.button(text="🕒 Напоминания",   callback_data="mg_time")
    kb.button(text="📝 Чек-ин",        callback_data="mg_now")
    kb.button(text="🌙 Записать сон",  callback_data="mg_dream_now")
    kb.button(text="🔑 Пароль",        callback_data="mg_pass")      # ← новая
    kb.button(text="📦 Экспорт",       callback_data="mg_export")
    kb.adjust(1)
    return kb.as_markup()


@router.message(Command("menu"))
async def menu(msg: types.Message):
    if msg.from_user.id in AUTHORIZED_USER_IDS:
        await msg.answer("Меню:", reply_markup=main_kb())


# ───── пароль подменю ─────────────────────────────────────
@router.callback_query(lambda c: c.data == "mg_pass")
async def pass_menu(cq: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔐 Установить", callback_data="pass_set")
    kb.button(text="🔓 Войти",      callback_data="pass_login")
    kb.button(text="⬅️",            callback_data="mg_back")
    kb.adjust(1)
    await cq.message.edit_text("Пароль:", reply_markup=kb.as_markup())
    await cq.answer()


@router.callback_query(lambda c: c.data in ("pass_set", "pass_login"))
async def pass_actions(cq: types.CallbackQuery, bot: Bot):
    prompt = "Введите новый пароль:" if cq.data == "pass_set" else "Введите пароль:"
    await bot.send_message(
        cq.from_user.id,
        prompt,
        reply_markup=types.ForceReply()
    )
    target = auth._wait_set if cq.data == "pass_set" else auth._wait_login
    target.add(cq.from_user.id)
    await cq.answer()


# ───── кнопка «📚 Сны»  → календарь  ──────────────────────
@router.callback_query(lambda c: c.data == "mg_dreams")
async def dreams_button(cq: types.CallbackQuery, bot: Bot):
    lst = view_dreams.dates_with_dreams(cq.from_user.id)
    if not lst:
        await bot.send_message(cq.from_user.id, "Нет сохранённых снов.")
        await cq.answer(); return
    kb = view_dreams.kb_calendar(lst, page=0)
    await bot.send_message(cq.from_user.id, "Выбери дату:", reply_markup=kb)
    await cq.answer()

# ───── кнопка Чек-ин сейчас ───────────────────────────────
@router.callback_query(lambda c: c.data == "mg_now")
async def now_ci(cq: types.CallbackQuery, bot: Bot):
    await bot.send_message(cq.from_user.id, "Быстрый чек-ин.")
    await mood.start(bot, cq.from_user.id)
    await cq.answer()


# ───── кнопка Запись сна сейчас ───────────────────────────
@router.callback_query(lambda c: c.data == "mg_dream_now")
async def dream_now(cq: types.CallbackQuery, bot: Bot):
    from handlers import dreams
    await dreams.start_record(bot, cq.from_user.id)
    await cq.answer()


# ───── кнопка Сны  → /dreams ──────────────────────────────
@router.callback_query(lambda c: c.data == "mg_dreams")
async def dreams_button(cq: types.CallbackQuery, bot: Bot):
    """
    Открываем календарь с датами, где действительно есть текст снов.
    Без фейковых Message — формируем ответ напрямую.
    """
    uid = cq.from_user.id
    lst = view_dreams.dates_with_dreams(uid)

    if not lst:
        await bot.send_message(uid, "Нет сохранённых снов.")
        await cq.answer()
        return

    kb = view_dreams.kb_calendar(lst)
    await bot.send_message(uid, "Выбери дату:", reply_markup=kb)
    await cq.answer()


# ───── кнопка График ───────────────────────────────────────
@router.callback_query(lambda c: c.data == "mg_graph")
async def g_period(cq: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for p, t in [
        ("all", "Весь доступный диапазон"),
        ("year", "Год"),
        ("month", "Месяц"),
        ("week", "Неделя"),
    ]:
        kb.button(text=t, callback_data=f"gp_set_{p}")
    kb.button(text="⬅️", callback_data="mg_back")
    kb.adjust(1)
    await _edit(cq.message, "Период:", kb.as_markup())
    await cq.answer()


@router.callback_query(lambda c: c.data.startswith("gp_set_"))
async def g_choose_param(cq: types.CallbackQuery):
    period = cq.data.split("_", 2)[2]
    st = _graph_state.setdefault(cq.from_user.id, GraphState())
    st.period = period
    st.page = 0
    st.params = []
    st.msg_id = None
    kb = InlineKeyboardBuilder()
    for k, l in GRAPH_PARAMS:
        kb.button(text=l, callback_data=f"gp_add_{k}")
    kb.button(text="⬅️", callback_data="mg_graph")
    kb.adjust(2)
    await cq.message.edit_text("Параметр:", reply_markup=kb.as_markup())
    await cq.answer()


async def _show_graph(bot: Bot, uid: int, st: GraphState, message: types.Message):
    path = user_dir(uid) / "plot.png"
    res = plot_multi(uid, st.params, st.period, str(path), st.page)
    kb = InlineKeyboardBuilder()
    if st.period != "all":
        kb.button(text="⬅️", callback_data="gprev")
        kb.button(text="➡️", callback_data="gnext")
    kb.adjust(2)
    kb.button(text="Выбрать другой параметр", callback_data="g_new")
    if len(st.params) < len(GRAPH_PARAMS):
        kb.button(text="Выбрать дополнительный параметр", callback_data="g_more")
    kb.adjust(1)
    kb.button(text="⬅️ Меню", callback_data="mg_back")
    if st.msg_id:
        try:
            await bot.delete_message(uid, st.msg_id)
        except Exception:
            pass
    if res:
        msg = await bot.send_photo(uid, FSInputFile(res), reply_markup=kb.as_markup())
    else:
        msg = await bot.send_message(uid, "Нет данных.", reply_markup=kb.as_markup())
    st.msg_id = msg.message_id


@router.callback_query(lambda c: c.data.startswith("gp_add_"))
async def g_first_param(cq: types.CallbackQuery, bot: Bot):
    param = cq.data.split("_", 2)[2]
    st = _graph_state.setdefault(cq.from_user.id, GraphState())
    st.params = [param]
    await _show_graph(bot, cq.from_user.id, st, cq.message)
    await cq.answer()


@router.callback_query(lambda c: c.data == "g_new")
async def g_new_param(cq: types.CallbackQuery):
    st = _graph_state.get(cq.from_user.id)
    if st and st.msg_id:
        try:
            await cq.bot.delete_message(cq.from_user.id, st.msg_id)
        except Exception:
            pass
        st.msg_id = None
    kb = InlineKeyboardBuilder()
    for k, l in GRAPH_PARAMS:
        kb.button(text=l, callback_data=f"gp_add_{k}")
    kb.button(text="⬅️", callback_data="mg_graph")
    kb.adjust(2)
    await cq.bot.send_message(cq.from_user.id, "Параметр:", reply_markup=kb.as_markup())
    if st:
        st.params = []
    await cq.answer()


@router.callback_query(lambda c: c.data == "g_more")
async def g_more_param(cq: types.CallbackQuery):
    st = _graph_state.get(cq.from_user.id)
    if not st:
        await cq.answer(); return
    kb = InlineKeyboardBuilder()
    remaining = [k for k, _ in GRAPH_PARAMS if k not in st.params]
    for k, l in GRAPH_PARAMS:
        if k in remaining:
            kb.button(text=l, callback_data=f"ga_{k}")
    if remaining:
        kb.button(text="Добавить все", callback_data="ga_all")
    kb.button(text="⬅️", callback_data="g_cancel")
    kb.adjust(2)
    await _edit(cq.message, "Дополнительный параметр:", kb.as_markup())
    await cq.answer()


@router.callback_query(lambda c: c.data == "g_cancel")
async def g_cancel_more(cq: types.CallbackQuery, bot: Bot):
    st = _graph_state.get(cq.from_user.id)
    if not st:
        await cq.answer(); return
    await _show_graph(bot, cq.from_user.id, st, cq.message)
    await cq.answer()


@router.callback_query(lambda c: c.data.startswith("ga_") or c.data == "ga_all")
async def g_add_param(cq: types.CallbackQuery, bot: Bot):
    st = _graph_state.get(cq.from_user.id)
    if not st:
        await cq.answer(); return
    if cq.data == "ga_all":
        st.params = [k for k, _ in GRAPH_PARAMS]
    else:
        param = cq.data.split("_", 1)[1]
        if param not in st.params:
            st.params.append(param)
    await _show_graph(bot, cq.from_user.id, st, cq.message)
    await cq.answer()


@router.callback_query(lambda c: c.data in ("gprev", "gnext"))
async def g_nav(cq: types.CallbackQuery, bot: Bot):
    st = _graph_state.get(cq.from_user.id)
    if not st:
        await cq.answer(); return
    if cq.data == "gprev":
        st.page += 1
    else:
        st.page = max(0, st.page - 1)
    await _show_graph(bot, cq.from_user.id, st, cq.message)
    await cq.answer()


# ───── CIM-анализ ─────────────────────────────────────────
@router.callback_query(lambda c: c.data == "mg_cim")
async def cim_period(cq: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for p, t in [
        ("all", "Весь доступный диапазон"),
        ("year", "Год"),
        ("month", "Месяц"),
        ("week", "Неделя"),
    ]:
        kb.button(text=t, callback_data=f"cp_set_{p}")
    kb.button(text="⬅️", callback_data="mg_back")
    kb.adjust(1)
    await _edit(cq.message, "Период:", kb.as_markup())
    await cq.answer()


@router.callback_query(lambda c: c.data.startswith("cp_set_"))
async def cim_choose_param(cq: types.CallbackQuery):
    period = cq.data.split("_", 2)[2]
    st = _cim_state.setdefault(cq.from_user.id, GraphState())
    st.period = period
    st.page = 0
    st.params = []
    st.msg_id = None
    kb = InlineKeyboardBuilder()
    for e in CIM_EMOTIONS:
        kb.button(text=e, callback_data=f"cp_add_{e}")
    kb.button(text="⬅️", callback_data="mg_cim")
    kb.adjust(2)
    await _edit(cq.message, "Эмоция:", kb.as_markup())
    await cq.answer()


async def _show_cim(bot: Bot, uid: int, st: GraphState, message: types.Message):
    path = user_dir(uid) / "cim_plot.png"
    params = [f"emo_{p}" for p in st.params]
    res = plot_multi(uid, params, st.period, str(path), st.page)
    kb = InlineKeyboardBuilder()
    if st.period != "all":
        kb.button(text="⬅️", callback_data="cprev")
        kb.button(text="➡️", callback_data="cnext")
    kb.adjust(2)
    kb.button(text="Выбрать другую эмоцию", callback_data="c_new")
    if len(st.params) < len(CIM_EMOTIONS):
        kb.button(text="Добавить эмоцию", callback_data="c_more")
    kb.adjust(1)
    kb.button(text="⬅️ Меню", callback_data="mg_back")

    if st.msg_id:
        try:
            await bot.delete_message(uid, st.msg_id)
        except Exception:
            pass
    if res:
        msg = await bot.send_photo(uid, FSInputFile(res), reply_markup=kb.as_markup())
    else:
        msg = await bot.send_message(uid, "Нет данных.", reply_markup=kb.as_markup())
    st.msg_id = msg.message_id


@router.callback_query(lambda c: c.data.startswith("cp_add_"))
async def cim_first_param(cq: types.CallbackQuery, bot: Bot):
    param = cq.data.split("_", 2)[2]
    st = _cim_state.setdefault(cq.from_user.id, GraphState())
    st.params = [param]
    await _show_cim(bot, cq.from_user.id, st, cq.message)
    await cq.answer()


@router.callback_query(lambda c: c.data == "c_new")
async def cim_new_param(cq: types.CallbackQuery):
    st = _cim_state.get(cq.from_user.id)
    if st and st.msg_id:
        try:
            await cq.bot.delete_message(cq.from_user.id, st.msg_id)
        except Exception:
            pass
        st.msg_id = None
    kb = InlineKeyboardBuilder()
    for e in CIM_EMOTIONS:
        kb.button(text=e, callback_data=f"cp_add_{e}")
    kb.button(text="⬅️", callback_data="mg_cim")
    kb.adjust(2)
    await _edit(cq.message, "Эмоция:", kb.as_markup())
    if st:
        st.params = []
    await cq.answer()


@router.callback_query(lambda c: c.data == "c_more")
async def cim_more_param(cq: types.CallbackQuery):
    st = _cim_state.get(cq.from_user.id)
    if not st:
        await cq.answer(); return
    kb = InlineKeyboardBuilder()
    remaining = [e for e in CIM_EMOTIONS if e not in st.params]
    for e in remaining:
        kb.button(text=e, callback_data=f"ca_{e}")
    if remaining:
        kb.button(text="Добавить все", callback_data="ca_all")
    kb.button(text="⬅️", callback_data="c_cancel")
    kb.adjust(2)
    await _edit(cq.message, "Дополнительная эмоция:", kb.as_markup())
    await cq.answer()


@router.callback_query(lambda c: c.data == "c_cancel")
async def cim_cancel_more(cq: types.CallbackQuery, bot: Bot):
    st = _cim_state.get(cq.from_user.id)
    if not st:
        await cq.answer(); return
    await _show_cim(bot, cq.from_user.id, st, cq.message)
    await cq.answer()


@router.callback_query(lambda c: c.data.startswith("ca_") or c.data == "ca_all")
async def cim_add_param(cq: types.CallbackQuery, bot: Bot):
    st = _cim_state.get(cq.from_user.id)
    if not st:
        await cq.answer(); return
    if cq.data == "ca_all":
        st.params = list(CIM_EMOTIONS)
    else:
        param = cq.data.split("_", 1)[1]
        if param not in st.params:
            st.params.append(param)
    await _show_cim(bot, cq.from_user.id, st, cq.message)
    await cq.answer()


@router.callback_query(lambda c: c.data in ("cprev", "cnext"))
async def cim_nav(cq: types.CallbackQuery, bot: Bot):
    st = _cim_state.get(cq.from_user.id)
    if not st:
        await cq.answer(); return
    if cq.data == "cprev":
        st.page += 1
    else:
        st.page = max(0, st.page - 1)
    await _show_cim(bot, cq.from_user.id, st, cq.message)
    await cq.answer()


# ───── кнопка FFT ─────────────────────────────────────────
@router.callback_query(lambda c: c.data == "mg_fft")
async def fft_param(cq: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for k, l in GRAPH_PARAMS:
        kb.button(text=l, callback_data=f"f_{k}")
    kb.button(text="⬅️", callback_data="mg_back")
    kb.adjust(2)
    await cq.message.edit_text("FFT параметр:", reply_markup=kb.as_markup())
    await cq.answer()


@router.callback_query(lambda c: re.match(r"f_\\w+", c.data))
async def send_fft(cq: types.CallbackQuery, bot: Bot):
    param = cq.data[2:]
    path = user_dir(cq.from_user.id) / f"{param}_fft.png"
    res = save_fft(cq.from_user.id, param, str(path))
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Меню", callback_data="mg_back")
    if res:
        await bot.send_photo(cq.from_user.id, photo=FSInputFile(res), reply_markup=kb.as_markup())
    else:
        await bot.send_message(cq.from_user.id, "Нет данных.", reply_markup=kb.as_markup())
    await cq.answer()


# ───── кнопка Напоминания ─────────────────────────────────
@router.callback_query(lambda c: c.data == "mg_time")
async def time_view(cq: types.CallbackQuery):
    m, e = load_user_times(cq.from_user.id)
    await cq.message.edit_text(
        f"Утро  {m.strftime('%H:%M')}\nВечер {e.strftime('%H:%M')}\n"
        f"Измени:  /set HH:MM HH:MM",
        reply_markup=main_kb()
    )
    await cq.answer()


# ───── кнопка Экспорт ─────────────────────────────────────
@router.callback_query(lambda c: c.data == "mg_export")
async def exp(cq: types.CallbackQuery, bot: Bot):
    path = export(cq.from_user.id)
    await bot.send_document(cq.from_user.id, open(path, "rb"), caption="Экспорт")
    await cq.answer()


# ───── кнопка Пропуски ────────────────────────────────────
# (роутер missed уже подключён в bot.py)
# здесь ничего менять не нужно


# ───── Назад ──────────────────────────────────────────────
@router.callback_query(lambda c: c.data == "mg_back")
async def back(cq: types.CallbackQuery):
    try:
        await cq.message.delete()
    except Exception:
        pass
    await cq.message.answer("Меню:", reply_markup=main_kb())
    await cq.answer()
