#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
# Copyright (C) 2021-present by diasera@Github, < https://github.com/diasera >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import time

from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup

import config
from strings import get_string
from YukkiMusic.misc import db
from YukkiMusic.utils.database import (get_active_chats, get_lang,
                                       is_music_playing)
from YukkiMusic.utils.formatters import seconds_to_min
from YukkiMusic.utils.inline import (stream_markup_timer,
                                     telegram_markup_timer)
from YukkiMusic.utils.tasks import create_task

from ..admins.callback import wrong

# chat id -> monotonic time until which Telegram asked us not to edit there
flood_until = {}


async def timer():
    while not await asyncio.sleep(1):
        active_chats = await get_active_chats()
        for chat_id in active_chats:
            if not await is_music_playing(chat_id):
                continue
            playing = db.get(chat_id)
            if not playing:
                continue
            file_path = playing[0]["file"]
            if "index_" in file_path or "live_" in file_path:
                continue
            duration = int(playing[0]["seconds"])
            if duration == 0:
                continue
            db[chat_id][0]["played"] += 1


create_task(timer(), "timer")


async def markup_timer():
    while not await asyncio.sleep(config.PLAYER_UPDATE_INTERVAL):
        active_chats = await get_active_chats()
        now = time.monotonic()
        for chat_id in list(flood_until):
            if flood_until[chat_id] <= now:
                del flood_until[chat_id]
        # copy: chats can stop playing while this loop awaits Telegram
        for chat_id in list(active_chats):
            if chat_id in flood_until:
                continue
            try:
                if not await is_music_playing(chat_id):
                    continue
                playing = db.get(chat_id)
                if not playing:
                    continue
                duration_seconds = int(playing[0]["seconds"])
                if duration_seconds == 0:
                    continue
                try:
                    mystic = playing[0]["mystic"]
                    markup = playing[0]["markup"]
                except Exception:
                    continue
                try:
                    check = wrong[chat_id][mystic.id]
                    if check is False:
                        continue
                except Exception:
                    pass
                try:
                    language = await get_lang(chat_id)
                    _ = get_string(language)
                except Exception:
                    _ = get_string("en")
                try:
                    buttons = (
                        stream_markup_timer(
                            _,
                            playing[0]["vidid"],
                            chat_id,
                            seconds_to_min(playing[0]["played"]),
                            playing[0]["dur"],
                        )
                        if markup == "stream"
                        else telegram_markup_timer(
                            _,
                            chat_id,
                            seconds_to_min(playing[0]["played"]),
                            playing[0]["dur"],
                        )
                    )
                    await mystic.edit_reply_markup(
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                except FloodWait as e:
                    flood_until[chat_id] = time.monotonic() + e.value
                except Exception:
                    continue
            except Exception:
                continue


create_task(markup_timer(), "markup_timer")
