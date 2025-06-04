# handlers/auth.py
# ───────────────────────────────────────────────────────────
from __future__ import annotations
import asyncio
from typing import Dict, Set

from aiogram import Router, Bot, types
from aiogram.filters import Command
from Token import AUTHORIZED_USER_IDS

router = Router()

_cache: Dict[int, str] = {}          # пароли в RAM
_wait_set: Set[int] = set()          # ждём новый пароль
_wait_login: Set[int] = set()        # ждём ввод пароля
TIMEOUT = 180                        # 3 минуты


# ───────────────────────────────────────────────────────────
async def _ask_password(bot: Bot, uid: int, mode: str):
    prompt = "Введите новый пароль:" if mode == "set" else "Введите пароль:"
    await bot.send_message(uid, prompt, reply_markup=types.ForceReply())
    ( _wait_set if mode == "set" else _wait_login ).add(uid)
    asyncio.create_task(_timeout(uid, mode, bot))


async def _timeout(uid: int, mode: str, bot: Bot):
    await asyncio.sleep(TIMEOUT)
    wait = _wait_set if mode == "set" else _wait_login
    if uid in wait:
        wait.discard(uid)
        await bot.send_message(uid, "⏳ Время ожидания истекло.")


def start_set(bot: Bot, uid: int):
    asyncio.create_task(_ask_password(bot, uid, "set"))


def start_login(bot: Bot, uid: int):
    asyncio.create_task(_ask_password(bot, uid, "login"))


# ───────────────────────────────────────────────────────────
@router.message(lambda m: m.from_user.id in _wait_set)
async def got_new_pass(msg: types.Message):
    _wait_set.discard(msg.from_user.id)
    _cache[msg.from_user.id] = msg.text
    await _safe_delete(msg)
    await msg.bot.send_message(msg.chat.id, "🔑 Пароль установлен.")


@router.message(lambda m: m.from_user.id in _wait_login)
async def got_login(msg: types.Message):
    _wait_login.discard(msg.from_user.id)
    _cache[msg.from_user.id] = msg.text
    await _safe_delete(msg)
    await msg.bot.send_message(msg.chat.id, "✅ Пароль принят.")


async def _safe_delete(msg: types.Message):
    try:
        await msg.bot.delete_message(msg.chat.id, msg.message_id)
    except Exception:
        pass


# ───────────────────────────────────────────────────────────
# Команды CLI (остались для продвинутого режима)
# ───────────────────────────────────────────────────────────
@router.message(Command("setpass"))
async def cmd_set(msg: types.Message):
    if msg.from_user.id in AUTHORIZED_USER_IDS:
        _cache[msg.from_user.id] = msg.text.split(maxsplit=1)[1]
        await msg.reply("🔑 Пароль установлен.")


@router.message(Command("login"))
async def cmd_log(msg: types.Message):
    if msg.from_user.id in AUTHORIZED_USER_IDS:
        _cache[msg.from_user.id] = msg.text.split(maxsplit=1)[1]
        await msg.reply("✅ Пароль принят.")


# ───────────────────────────────────────────────────────────
def get_pass(uid: int) -> str | None:
    return _cache.get(uid)
