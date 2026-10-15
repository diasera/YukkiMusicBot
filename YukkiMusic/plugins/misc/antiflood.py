#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
# Copyright (C) 2021-present by diasera@Github, < https://github.com/diasera >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import math
import os
import traceback

from pyrogram import StopPropagation, raw, utils
from pyrogram.errors import FloodWait, SlowmodeWait
from pyrogram.types import CallbackQuery

import config
from config import BANNED_USERS
from strings import get_string
from YukkiMusic import LOGGER, app
from YukkiMusic.utils.cache import Cooldown
from YukkiMusic.utils.database import get_lang

# Folder that holds the bot package, used to point at the line that hit the limit
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
PACKAGE = os.path.join(ROOT, "YukkiMusic", "")

cooldown = Cooldown(config.CALLBACK_COOLDOWN)
# Only the first blocked press of a cooldown gets a reply, the rest are dropped
warned = Cooldown(config.CALLBACK_COOLDOWN)


async def strings_for(chat_id: int = None):
    try:
        return get_string(await get_lang(chat_id))
    except Exception:
        return get_string("en")


@app.on_callback_query(~BANNED_USERS, group=-1)
async def callback_cooldown(client, query: CallbackQuery):
    left = cooldown.hit(query.from_user.id)
    if not left:
        return
    if not warned.hit(query.from_user.id):
        _ = await strings_for(query.message.chat.id if query.message else None)
        try:
            await query.answer(_["general_7"].format(math.ceil(left)))
        except Exception:
            pass
    raise StopPropagation


@app.on_error((FloodWait, SlowmodeWait))
async def flood_error(client, error, handler, update, users, chats):
    frames = traceback.extract_tb(error.__traceback__)
    origin = next(
        (f for f in reversed(frames) if f.filename.startswith(PACKAGE)),
        None,
    )
    where = (
        f"{origin.filename[len(ROOT) + 1:]}:{origin.lineno}"
        if origin
        else type(update).__name__
    )
    LOGGER(__name__).warning(
        f"{type(error).__name__}: Telegram asked to wait {error.value}s ({where})"
    )
    if not isinstance(
        update,
        (raw.types.UpdateBotCallbackQuery, raw.types.UpdateInlineBotCallbackQuery),
    ):
        return
    chat_id = (
        utils.get_peer_id(update.peer)
        if isinstance(update, raw.types.UpdateBotCallbackQuery)
        else None
    )
    _ = await strings_for(chat_id)
    try:
        await client.answer_callback_query(
            str(update.query_id),
            _["general_8"].format(error.value),
            show_alert=True,
        )
    except Exception:
        pass
