import datetime, json
from aiogram import Router, types, Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.storage import user_dir
from handlers import mood, dreams
router=Router()
def build_calendar(days_list, prefix):
    kb=InlineKeyboardBuilder()
    for d in days_list:
        label=d.strftime('%d.%m')
        kb.button(text=label, callback_data=f"{prefix}_{d.isoformat()}")
    kb.adjust(4)
    return kb.as_markup()
@router.callback_query(lambda c:c.data=="mg_missed")
async def choose_type(cq: types.CallbackQuery):
    kb=InlineKeyboardBuilder()
    kb.button(text="Чек‑ин", callback_data="missed_ci")
    kb.button(text="Сон", callback_data="missed_dream")
    kb.button(text="⬅️", callback_data="mg_back")
    kb.adjust(1)
    await cq.message.edit_text("Что добавить?", reply_markup=kb.as_markup())
    await cq.answer()
def get_missing_dates(uid, sub):
    folder=user_dir(uid)/sub
    existing={f.name.split('_')[1] for f in folder.glob(f'{sub[:-1]}_*')} if folder.exists() else set()
    today=datetime.date.today()
    dates=[today-datetime.timedelta(days=i) for i in range(1,31)]
    return [d for d in dates if d.strftime('%Y%m%d') not in existing]
@router.callback_query(lambda c:c.data in ["missed_ci","missed_dream"])
async def show_calendar(cq: types.CallbackQuery):
    typ="mood" if cq.data=="missed_ci" else "dreams"
    days=get_missing_dates(cq.from_user.id, typ)
    if not days:
        await cq.answer("Пропусков нет"); return
    markup=build_calendar(days[:16],"ci" if typ=="mood" else "dr")
    await cq.message.edit_text("Выбери дату:", reply_markup=markup)
    await cq.answer()
@router.callback_query(lambda c: c.data.startswith('ci_'))
async def start_back_ci(cq: types.CallbackQuery, bot: Bot):
    date=cq.data.split('_',1)[1]
    await bot.send_message(cq.from_user.id, f"Чек‑ин за {date}")
    await mood.start(bot, cq.from_user.id, backdate=date)
    await cq.answer()
@router.callback_query(lambda c: c.data.startswith('dr_'))
async def start_back_dream(cq: types.CallbackQuery, bot: Bot):
    date=cq.data.split('_',1)[1]

    await bot.send_message(
        cq.from_user.id,
        f"Сон за {date}\nОтправь текст сообщением или кнопка:",
        reply_markup=dreams.dream_kb()
    )
    dreams._waiting[cq.from_user.id] = date  # ← ставим флажок
