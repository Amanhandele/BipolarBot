from aiogram import Bot

MAX_MESSAGE_LENGTH = 4096

async def send_long(bot: Bot, chat_id: int, text: str, **kwargs) -> None:
    """Send text in several messages if it exceeds Telegram limit."""
    remaining = text
    first = True
    while remaining:
        chunk = remaining[:MAX_MESSAGE_LENGTH]
        if len(chunk) == MAX_MESSAGE_LENGTH:
            cut = max(chunk.rfind('\n'), chunk.rfind(' '))
            if cut <= 0 or cut < MAX_MESSAGE_LENGTH - 100:
                cut = MAX_MESSAGE_LENGTH
            chunk = remaining[:cut]
        await bot.send_message(chat_id, chunk, **kwargs)
        if first and 'reply_to_message_id' in kwargs:
            del kwargs['reply_to_message_id']
            first = False
        remaining = remaining[len(chunk):].lstrip('\n')
