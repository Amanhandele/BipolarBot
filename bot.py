import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from Token import API_TOKEN, AUTHORIZED_USER_IDS
from config import load_user_times, save_user_times
from handlers import dreams, mood, manage, missed, view_dreams
logging.basicConfig(level=logging.INFO)
bot=Bot(API_TOKEN, parse_mode='HTML')
dp=Dispatcher()

# порядок подключения ВАЖЕН:
dp.include_router(dreams.router)
dp.include_router(mood.router)
dp.include_router(manage.router)
dp.include_router(missed.router)
dp.include_router(view_dreams.router)



sched=AsyncIOScheduler()


async def setup_commands():
    cmds = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="menu", description="Меню"),
        BotCommand(command="checkin", description="Быстрый чек-ин"),
        BotCommand(command="dream", description="Записать сон"),
        BotCommand(command="dreams", description="Архив снов"),
        BotCommand(command="set", description="Время уведомлений"),
    ]
    await bot.set_my_commands(cmds)

async def morning(uid:int):
    from handlers.dreams import dream_kb
    await bot.send_message(uid,"Доброе утро! /dream или кнопка:", reply_markup=dream_kb())
async def evening(uid:int):
    await bot.send_message(uid,"Вечерний чек‑ин.")
    await mood.start(bot, uid)
async def plan(uid: int):
    m, e = load_user_times(uid)
    sched.add_job(
        morning,
        "cron",
        args=[uid],
        hour=m.hour,
        minute=m.minute,
        id=f"m_{uid}",
        replace_existing=True,
    )
    sched.add_job(
        evening,
        "cron",
        args=[uid],
        hour=e.hour,
        minute=e.minute,
        id=f"e_{uid}",
        replace_existing=True,
    )
@dp.message(Command("start"))
async def cmd_start(msg: Message):
    if msg.from_user.id not in AUTHORIZED_USER_IDS:
        return
    from handlers.manage import main_kb
    await msg.answer("Меню:", reply_markup=main_kb())


@dp.message(Command("menu"))
async def cmd_menu(msg: Message):
    if msg.from_user.id not in AUTHORIZED_USER_IDS:
        return
    from handlers.manage import main_kb
    await msg.answer("Меню:", reply_markup=main_kb())
@dp.message(Command("set"))
async def cmd_set(msg: Message):
    if msg.from_user.id not in AUTHORIZED_USER_IDS:return
    parts=msg.text.split()
    if len(parts)!=3:
        await msg.reply("/set HH:MM HH:MM"); return
    save_user_times(msg.from_user.id, parts[1], parts[2])
    await plan(msg.from_user.id)
    await msg.reply("Установлено")

async def main():
    for uid in AUTHORIZED_USER_IDS: await plan(uid)
    await setup_commands()
    sched.start()
    await dp.start_polling(bot)
if __name__=='__main__':
    asyncio.run(main())
