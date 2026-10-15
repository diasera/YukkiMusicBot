#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait
from pyrogram.raw import types

import config
from config import adminlist, chatstats, clean, userstats
from strings import get_command
from YukkiMusic import LOGGER, app
from YukkiMusic.misc import SUDOERS
from YukkiMusic.utils.database import (get_active_chats,
                                       get_authuser_names, get_client,
                                       get_particular_top,
                                       get_served_chats,
                                       get_served_users, get_user_top,
                                       is_cleanmode_on, set_queries,
                                       update_particular_top,
                                       update_user_top)
from YukkiMusic.utils.decorators.admins import can_manage_vc
from YukkiMusic.utils.decorators.language import language
from YukkiMusic.utils.formatters import alpha_to_int
from YukkiMusic.utils.tasks import create_task

BROADCAST_COMMAND = get_command("BROADCAST_COMMAND")
AUTO_DELETE = config.CLEANMODE_DELETE_MINS
AUTO_SLEEP = 5
IS_BROADCASTING = False
cleanmode_group = 15


@app.on_raw_update(group=cleanmode_group)
async def clean_mode(client, update, users, chats):
    global IS_BROADCASTING
    if IS_BROADCASTING:
        return
    try:
        if not isinstance(update, types.UpdateReadChannelOutbox):
            return
    except Exception:
        return
    if users:
        return
    if chats:
        return
    message_id = update.max_id
    chat_id = int(f"-100{update.channel_id}")
    if not await is_cleanmode_on(chat_id):
        return
    if chat_id not in clean:
        clean[chat_id] = []
    time_now = datetime.now()
    put = {
        "msg_id": message_id,
        "timer_after": time_now + timedelta(minutes=AUTO_DELETE),
    }
    clean[chat_id].append(put)
    await set_queries(1)


@app.on_message(filters.command(BROADCAST_COMMAND) & SUDOERS)
@language
async def braodcast_message(client, message, _):
    global IS_BROADCASTING
    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_5"])
        query = message.text.split(None, 1)[1]
        if "-pin" in query:
            query = query.replace("-pin", "")
        if "-nobot" in query:
            query = query.replace("-nobot", "")
        if "-pinloud" in query:
            query = query.replace("-pinloud", "")
        if "-assistant" in query:
            query = query.replace("-assistant", "")
        if "-user" in query:
            query = query.replace("-user", "")
        if query == "":
            return await message.reply_text(_["broad_6"])

    IS_BROADCASTING = True

    # Bot broadcast inside chats
    if "-nobot" not in message.text:
        sent = 0
        pin = 0
        chats = []
        schats = await get_served_chats()
        for chat in schats:
            chats.append(int(chat["chat_id"]))
        for i in chats:
            if i == -1001733534088:
                continue
            try:
                m = (
                    await app.forward_messages(i, y, x)
                    if message.reply_to_message
                    else await app.send_message(i, text=query)
                )
                if "-pin" in message.text:
                    try:
                        await m.pin(disable_notification=True)
                        pin += 1
                    except Exception:
                        continue
                elif "-pinloud" in message.text:
                    try:
                        await m.pin(disable_notification=False)
                        pin += 1
                    except Exception:
                        continue
                sent += 1
            except FloodWait as e:
                flood_time = int(e.value)
                if flood_time > 200:
                    continue
                await asyncio.sleep(flood_time)
            except Exception:
                continue
        try:
            await message.reply_text(_["broad_1"].format(sent, pin))
        except Exception:
            pass

    # Bot broadcasting to users
    if "-user" in message.text:
        susr = 0
        served_users = []
        susers = await get_served_users()
        for user in susers:
            served_users.append(int(user["user_id"]))
        for i in served_users:
            try:
                m = (
                    await app.forward_messages(i, y, x)
                    if message.reply_to_message
                    else await app.send_message(i, text=query)
                )
                susr += 1
            except FloodWait as e:
                flood_time = int(e.value)
                if flood_time > 200:
                    continue
                await asyncio.sleep(flood_time)
            except Exception:
                pass
        try:
            await message.reply_text(_["broad_7"].format(susr))
        except Exception:
            pass

    # Bot broadcasting by assistant
    if "-assistant" in message.text:
        aw = await message.reply_text(_["broad_2"])
        text = _["broad_3"]
        from YukkiMusic.core.userbot import assistants

        for num in assistants:
            sent = 0
            client = await get_client(num)
            async for dialog in client.get_dialogs():
                if dialog.chat.id == -1001733534088:
                    continue
                try:
                    await client.forward_messages(
                        dialog.chat.id, y, x
                    ) if message.reply_to_message else await client.send_message(
                        dialog.chat.id, text=query
                    )
                    sent += 1
                except FloodWait as e:
                    flood_time = int(e.value)
                    if flood_time > 200:
                        continue
                    await asyncio.sleep(flood_time)
                except Exception as e:
                    LOGGER(__name__).warning(e)
                    continue
            text += _["broad_4"].format(num, sent)
        try:
            await aw.edit_text(text)
        except Exception:
            pass
    IS_BROADCASTING = False


async def save_play_stats():
    for stats, get_top, update_top in (
        (chatstats, get_particular_top, update_particular_top),
        (userstats, get_user_top, update_user_top),
    ):
        for key in list(stats):
            entries = stats[key]
            while entries:
                track = entries[0]
                spot = await get_top(key, track["vidid"])
                await update_top(
                    key,
                    track["vidid"],
                    {
                        "spot": spot["spot"] + 1 if spot else 1,
                        "title": track["title"],
                    },
                )
                # removed only once saved, so a database error retries it
                entries.pop(0)
            del stats[key]


async def delete_due_messages():
    now = datetime.now()
    for chat_id in list(clean):
        entries = clean[chat_id]
        if chat_id == config.LOG_GROUP_ID:
            del clean[chat_id]
            continue
        due = [x["msg_id"] for x in entries if x["timer_after"] < now]
        if not due:
            continue
        pending = [x for x in entries if x["timer_after"] >= now]
        if pending:
            clean[chat_id] = pending
        else:
            del clean[chat_id]
        for i in range(0, len(due), 100):
            try:
                await app.delete_messages(chat_id, due[i : i + 100])
            except FloodWait as e:
                retry = datetime.now() + timedelta(seconds=e.value)
                clean.setdefault(chat_id, []).extend(
                    {"msg_id": msg_id, "timer_after": retry}
                    for msg_id in due[i:]
                )
                break
            except Exception:
                break


async def load_admins():
    for chat_id in list(await get_active_chats()):
        if chat_id in adminlist:
            continue
        admins = []
        try:
            async for user in app.get_chat_members(
                chat_id, filter=ChatMembersFilter.ADMINISTRATORS
            ):
                if can_manage_vc(user):
                    admins.append(user.user.id)
            for user in await get_authuser_names(chat_id):
                admins.append(await alpha_to_int(user))
        except Exception:
            pass
        adminlist[chat_id] = admins


async def auto_clean():
    while not await asyncio.sleep(AUTO_SLEEP):
        for job in (save_play_stats, delete_due_messages, load_admins):
            try:
                await job()
            except Exception as e:
                LOGGER(__name__).warning(f"{job.__name__} failed: {e}")


create_task(auto_clean(), "auto_clean")
