#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
# Copyright (C) 2021-present by diasera@Github, < https://github.com/diasera >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram import filters
from pyrogram.types import Message

from config import BANNED_USERS
from strings import get_command
from YukkiMusic import app
from YukkiMusic.core.call import Yukki
from YukkiMusic.misc import db
from YukkiMusic.utils.database import get_loop
from YukkiMusic.utils.decorators import AdminRightsCheck

# Commands
SKIP_COMMAND = get_command("SKIP_COMMAND")


@app.on_message(
    filters.command(SKIP_COMMAND)
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def skip(cli, message: Message, _, chat_id):
    lock = Yukki.chat_lock(chat_id)
    if lock.locked():
        return await message.reply_text(_["general_9"])
    async with lock:
        count = 1
        if len(message.command) > 1:
            if await get_loop(chat_id) != 0:
                return await message.reply_text(_["admin_12"])
            state = message.text.split(None, 1)[1].strip()
            if not state.isnumeric():
                return await message.reply_text(_["admin_13"])
            check = db.get(chat_id)
            if not check:
                return await message.reply_text(_["queue_2"])
            if len(check) <= 2:
                return await message.reply_text(_["admin_14"])
            count, limit = int(state), len(check) - 1
            if not 1 <= count <= limit:
                return await message.reply_text(
                    _["admin_15"].format(limit)
                )
        if not await Yukki.pop_tracks(chat_id, count):
            await Yukki.stop_stream(chat_id)
            return await message.reply_text(
                _["admin_10"].format(message.from_user.first_name)
            )
        await Yukki.play_queued(chat_id)
