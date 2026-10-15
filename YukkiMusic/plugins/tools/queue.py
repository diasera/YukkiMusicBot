#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import os

from pyrogram import filters
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import CallbackQuery, InputMediaPhoto, Message

import config
from config import BANNED_USERS
from strings import get_command
from YukkiMusic import app
from YukkiMusic.misc import db
from YukkiMusic.utils import (Yukkibin, get_channeplayCB,
                              seconds_to_min)
from YukkiMusic.utils.database import (get_cmode, is_active_chat,
                                       is_music_playing)
from YukkiMusic.utils.decorators.language import language, languageCB
from YukkiMusic.utils.inline import queue_back_markup, queue_markup
from YukkiMusic.utils.tasks import create_task

###Commands
QUEUE_COMMAND = get_command("QUEUE_COMMAND")

# Only the newest /queue card of a chat keeps a live timer:
# chat id of the card -> (message id, task updating it)
timers = {}


def get_image(videoid):
    if os.path.isfile(f"cache/{videoid}.png"):
        return f"cache/{videoid}.png"
    else:
        return config.YOUTUBE_IMG_URL


def start_timer(mystic, _, chat_id, cplay, track, DUR):
    card_chat = mystic.chat.id
    stop_timer(card_chat)
    task = create_task(
        update_timer(mystic, _, chat_id, cplay, track, DUR),
        f"queue_timer_{card_chat}",
    )
    timers[card_chat] = (mystic.id, task)


def stop_timer(card_chat, message_id=None):
    entry = timers.get(card_chat)
    if entry and message_id in (None, entry[0]):
        del timers[card_chat]
        entry[1].cancel()


async def update_timer(mystic, _, chat_id, cplay, track, DUR):
    """Refresh the played-time button until the track on the card ends."""
    try:
        while True:
            await asyncio.sleep(config.PLAYER_UPDATE_INTERVAL)
            playing = db.get(chat_id)
            if not playing or playing[0] is not track:
                return
            if not await is_active_chat(chat_id):
                return
            if not await is_music_playing(chat_id):
                continue
            buttons = queue_markup(
                _,
                DUR,
                cplay,
                track["vidid"],
                seconds_to_min(track["played"]),
                track["dur"],
            )
            try:
                await mystic.edit_reply_markup(reply_markup=buttons)
            except MessageNotModified:
                pass
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception:
                return
    finally:
        entry = timers.get(mystic.chat.id)
        if entry and entry[1] is asyncio.current_task():
            del timers[mystic.chat.id]


def get_duration(playing):
    file_path = playing[0]["file"]
    if "index_" in file_path or "live_" in file_path:
        return "Unknown"
    duration_seconds = int(playing[0]["seconds"])
    if duration_seconds == 0:
        return "Unknown"
    else:
        return "Inline"


@app.on_message(
    filters.command(QUEUE_COMMAND) & filters.group & ~BANNED_USERS
)
@language
async def ping_com(client, message: Message, _):
    if message.command[0][0] == "c":
        chat_id = await get_cmode(message.chat.id)
        if chat_id is None:
            return await message.reply_text(_["setting_12"])
        try:
            await app.get_chat(chat_id)
        except Exception:
            return await message.reply_text(_["cplay_4"])
        cplay = True
    else:
        chat_id = message.chat.id
        cplay = False
    if not await is_active_chat(chat_id):
        return await message.reply_text(_["general_6"])
    got = db.get(chat_id)
    if not got:
        return await message.reply_text(_["queue_2"])
    file = got[0]["file"]
    videoid = got[0]["vidid"]
    user = got[0]["by"]
    title = (got[0]["title"]).title()
    typo = (got[0]["streamtype"]).title()
    DUR = get_duration(got)
    if "live_" in file:
        IMAGE = get_image(videoid)
    elif "vid_" in file:
        IMAGE = get_image(videoid)
    elif "index_" in file:
        IMAGE = config.STREAM_IMG_URL
    else:
        if videoid == "telegram":
            IMAGE = (
                config.TELEGRAM_AUDIO_URL
                if typo == "Audio"
                else config.TELEGRAM_VIDEO_URL
            )
        elif videoid == "soundcloud":
            IMAGE = config.SOUNCLOUD_IMG_URL
        else:
            IMAGE = get_image(videoid)
    send = (
        "**⌛️Duration:** Unknown Duration Stream\n\nClick on button below to get whole queued list."
        if DUR == "Unknown"
        else "\nClick on button below to get whole queued list."
    )
    cap = f"""**{config.MUSIC_BOT_NAME} Player**

🎥**Playing:** {title}

🔗**Stream Type:** {typo}
🙍‍♂️**Played By:** {user}
{send}"""
    upl = (
        queue_markup(_, DUR, "c" if cplay else "g", videoid)
        if DUR == "Unknown"
        else queue_markup(
            _,
            DUR,
            "c" if cplay else "g",
            videoid,
            seconds_to_min(got[0]["played"]),
            got[0]["dur"],
        )
    )
    mystic = await message.reply_photo(
        IMAGE, caption=cap, reply_markup=upl
    )
    if DUR != "Unknown":
        start_timer(
            mystic, _, chat_id, "c" if cplay else "g", got[0], DUR
        )


@app.on_callback_query(filters.regex("GetTimer") & ~BANNED_USERS)
async def quite_timer(client, CallbackQuery: CallbackQuery):
    try:
        await CallbackQuery.answer()
    except Exception:
        pass


@app.on_callback_query(filters.regex("GetQueued") & ~BANNED_USERS)
@languageCB
async def queued_tracks(client, CallbackQuery: CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    what, videoid = callback_request.split("|")
    try:
        chat_id, channel = await get_channeplayCB(
            _, what, CallbackQuery
        )
    except Exception:
        return
    if not await is_active_chat(chat_id):
        return await CallbackQuery.answer(
            _["general_6"], show_alert=True
        )
    got = db.get(chat_id)
    if not got:
        return await CallbackQuery.answer(
            _["queue_2"], show_alert=True
        )
    if len(got) == 1:
        return await CallbackQuery.answer(
            _["queue_5"], show_alert=True
        )
    await CallbackQuery.answer()
    stop_timer(CallbackQuery.message.chat.id, CallbackQuery.message.id)
    buttons = queue_back_markup(_, what)
    med = InputMediaPhoto(
        media="https://telegra.ph//file/6f7d35131f69951c74ee5.jpg",
        caption=_["queue_1"],
    )
    await CallbackQuery.edit_message_media(media=med)
    j = 0
    msg = ""
    for x in got:
        j += 1
        if j == 1:
            msg += f'Currently Playing:\n\n🏷Title: {x["title"]}\nDuration: {x["dur"]}\nBy: {x["by"]}\n\n'
        elif j == 2:
            msg += f'Queued:\n\n🏷Title: {x["title"]}\nDuration: {x["dur"]}\nBy: {x["by"]}\n\n'
        else:
            msg += f'🏷Title: {x["title"]}\nDuration: {x["dur"]}\nBy: {x["by"]}\n\n'
    if "Queued" in msg:
        if len(msg) < 700:
            await asyncio.sleep(1)
            return await CallbackQuery.edit_message_text(
                msg, reply_markup=buttons
            )
        if "🏷" in msg:
            msg = msg.replace("🏷", "")
        link = await Yukkibin(msg)
        med = InputMediaPhoto(
            media=link, caption=_["queue_3"].format(link)
        )
        await CallbackQuery.edit_message_media(
            media=med, reply_markup=buttons
        )
    else:
        await asyncio.sleep(1)
        return await CallbackQuery.edit_message_text(
            msg, reply_markup=buttons
        )


@app.on_callback_query(
    filters.regex("queue_back_timer") & ~BANNED_USERS
)
@languageCB
async def queue_back(client, CallbackQuery: CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    cplay = callback_data.split(None, 1)[1]
    try:
        chat_id, channel = await get_channeplayCB(
            _, cplay, CallbackQuery
        )
    except Exception:
        return
    if not await is_active_chat(chat_id):
        return await CallbackQuery.answer(
            _["general_6"], show_alert=True
        )
    got = db.get(chat_id)
    if not got:
        return await CallbackQuery.answer(
            _["queue_2"], show_alert=True
        )
    await CallbackQuery.answer(_["set_cb_8"], show_alert=True)
    file = got[0]["file"]
    videoid = got[0]["vidid"]
    user = got[0]["by"]
    title = (got[0]["title"]).title()
    typo = (got[0]["streamtype"]).title()
    DUR = get_duration(got)
    if "live_" in file:
        IMAGE = get_image(videoid)
    elif "vid_" in file:
        IMAGE = get_image(videoid)
    elif "index_" in file:
        IMAGE = config.STREAM_IMG_URL
    else:
        if videoid == "telegram":
            IMAGE = (
                config.TELEGRAM_AUDIO_URL
                if typo == "Audio"
                else config.TELEGRAM_VIDEO_URL
            )
        elif videoid == "soundcloud":
            IMAGE = config.SOUNCLOUD_IMG_URL
        else:
            IMAGE = get_image(videoid)
    send = (
        "**⌛️Duration:** Unknown Duration Stream\n\nClick on button below to get whole queued list."
        if DUR == "Unknown"
        else "\nClick on button below to get whole queued list."
    )
    cap = f"""**{config.MUSIC_BOT_NAME} Player**

🎥**Playing:** {title}

🔗**Stream Type:** {typo}
🙍‍♂️**Played By:** {user}
{send}"""
    upl = (
        queue_markup(_, DUR, cplay, videoid)
        if DUR == "Unknown"
        else queue_markup(
            _,
            DUR,
            cplay,
            videoid,
            seconds_to_min(got[0]["played"]),
            got[0]["dur"],
        )
    )
    med = InputMediaPhoto(media=IMAGE, caption=cap)
    mystic = await CallbackQuery.edit_message_media(
        media=med, reply_markup=upl
    )
    if DUR != "Unknown":
        start_timer(mystic, _, chat_id, cplay, got[0], DUR)
