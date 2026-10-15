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
from typing import Union
from weakref import WeakValueDictionary

from ntgcalls import TelegramServerError
from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import (ChatAdminRequired,
                             UserAlreadyParticipant,
                             UserNotParticipant)
from pyrogram.types import InlineKeyboardMarkup, LinkPreviewOptions
from pytgcalls import PyTgCalls
from pytgcalls import filters as call_filters
from pytgcalls.exceptions import NoActiveGroupCall
from pytgcalls.types import (ChatUpdate, GroupCallConfig,
                             GroupCallParticipant, MediaStream,
                             StreamEnded, UpdatedGroupCallParticipant)

import config
from strings import get_string
from YukkiMusic import LOGGER, YouTube, app
from YukkiMusic.misc import db
from YukkiMusic.utils.database import (add_active_chat,
                                       add_active_video_chat,
                                       get_assistant,
                                       get_audio_bitrate, get_lang,
                                       get_loop, get_video_bitrate,
                                       group_assistant, is_autoend,
                                       music_on, mute_off,
                                       remove_active_chat,
                                       remove_active_video_chat,
                                       set_loop)
from YukkiMusic.utils.exceptions import AssistantErr
from YukkiMusic.utils.inline.play import (stream_markup,
                                          telegram_markup)
from YukkiMusic.utils.stream.autoclear import auto_clean
from YukkiMusic.utils.thumbnails import gen_thumb

autoend = {}
counter = {}
AUTO_END_TIME = 3

# Never start a voice chat automatically, raise NoActiveGroupCall instead
call_config = GroupCallConfig(auto_start=False)


async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call(PyTgCalls):
    def __init__(self):
        # Locks of chats that nobody is waiting on are dropped automatically,
        # so this never grows with the number of chats the bot has served.
        self._chat_locks = WeakValueDictionary()
        self.userbot1 = Client(
            "YukkiCall1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )
        self.one = PyTgCalls(
            self.userbot1,
            cache_duration=100,
        )
        self.userbot2 = Client(
            "YukkiCall2",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING2),
        )
        self.two = PyTgCalls(
            self.userbot2,
            cache_duration=100,
        )
        self.userbot3 = Client(
            "YukkiCall3",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING3),
        )
        self.three = PyTgCalls(
            self.userbot3,
            cache_duration=100,
        )
        self.userbot4 = Client(
            "YukkiCall4",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING4),
        )
        self.four = PyTgCalls(
            self.userbot4,
            cache_duration=100,
        )
        self.userbot5 = Client(
            "YukkiCall5",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING5),
        )
        self.five = PyTgCalls(
            self.userbot5,
            cache_duration=100,
        )

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause(chat_id)

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume(chat_id)

    async def mute_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.mute(chat_id)

    async def unmute_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.unmute(chat_id)

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_call(chat_id)
        except Exception:
            pass

    async def force_stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            check = db.get(chat_id)
            check.pop(0)
        except Exception:
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        try:
            await assistant.leave_call(chat_id)
        except Exception:
            pass

    def chat_lock(self, chat_id: int) -> asyncio.Lock:
        """Lock that serialises starting, skipping and ending tracks in a chat."""
        lock = self._chat_locks.get(chat_id)
        if lock is None:
            lock = self._chat_locks[chat_id] = asyncio.Lock()
        return lock

    async def media_stream(
        self, chat_id: int, path: str, video, ffmpeg_parameters=None
    ) -> MediaStream:
        audio_quality = await get_audio_bitrate(chat_id)
        if video:
            return MediaStream(
                path,
                audio_parameters=audio_quality,
                video_parameters=await get_video_bitrate(chat_id),
                ffmpeg_parameters=ffmpeg_parameters,
            )
        return MediaStream(
            path,
            audio_parameters=audio_quality,
            video_flags=MediaStream.Flags.IGNORE,
            ffmpeg_parameters=ffmpeg_parameters,
        )

    async def seek_stream(
        self, chat_id, file_path, to_seek, duration, mode
    ):
        assistant = await group_assistant(self, chat_id)
        stream = await self.media_stream(
            chat_id,
            file_path,
            mode == "video",
            ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
        )
        await assistant.play(chat_id, stream, config=call_config)

    async def stream_call(self, link):
        assistant = await group_assistant(self, config.LOG_GROUP_ID)
        await assistant.play(
            config.LOG_GROUP_ID,
            MediaStream(link),
            config=call_config,
        )
        await asyncio.sleep(0.5)
        await assistant.leave_call(config.LOG_GROUP_ID)

    async def join_assistant(self, original_chat_id, chat_id):
        language = await get_lang(original_chat_id)
        _ = get_string(language)
        userbot = await get_assistant(chat_id)
        try:
            try:
                get = await app.get_chat_member(chat_id, userbot.id)
            except ChatAdminRequired:
                raise AssistantErr(_["call_1"])
            if get.status == ChatMemberStatus.BANNED:
                raise AssistantErr(
                    _["call_2"].format(userbot.username, userbot.id)
                )
        except UserNotParticipant:
            chat = await app.get_chat(chat_id)
            if chat.username:
                try:
                    await userbot.join_chat(chat.username)
                except UserAlreadyParticipant:
                    pass
                except Exception as e:
                    raise AssistantErr(_["call_3"].format(e))
            else:
                try:
                    try:
                        try:
                            invitelink = chat.invite_link
                            if invitelink is None:
                                invitelink = (
                                    await app.export_chat_invite_link(
                                        chat_id
                                    )
                                )
                        except Exception:
                            invitelink = (
                                await app.export_chat_invite_link(
                                    chat_id
                                )
                            )
                    except ChatAdminRequired:
                        raise AssistantErr(_["call_4"])
                    except Exception as e:
                        raise AssistantErr(e)
                    m = await app.send_message(
                        original_chat_id, _["call_5"]
                    )
                    if invitelink.startswith("https://t.me/+"):
                        invitelink = invitelink.replace(
                            "https://t.me/+", "https://t.me/joinchat/"
                        )
                    await asyncio.sleep(3)
                    await userbot.join_chat(invitelink)
                    await asyncio.sleep(4)
                    await m.edit(_["call_6"].format(userbot.name))
                except UserAlreadyParticipant:
                    pass
                except Exception as e:
                    raise AssistantErr(_["call_3"].format(e))

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link,
        video: Union[bool, str] = None,
    ):
        assistant = await group_assistant(self, chat_id)
        stream = await self.media_stream(chat_id, link, video)
        # play() swaps the stream instead of failing when already joined
        if chat_id in await assistant.calls:
            raise AssistantErr(
                "**Assistant Already in Voice Chat**\n\nSystems have detected that assistant is already there in the voice chat, this issue generally comes when you play 2 queries together.\n\nIf assistant is not present in voice chat, please end voice chat and start fresh voice chat again and if the  problem continues, try /restart"
            )
        try:
            await assistant.play(
                chat_id,
                stream,
                config=call_config,
            )
        except NoActiveGroupCall:
            try:
                await self.join_assistant(original_chat_id, chat_id)
            except Exception as e:
                raise e
            try:
                await assistant.play(
                    chat_id,
                    stream,
                    config=call_config,
                )
            except Exception:
                raise AssistantErr(
                    "**No Active Voice Chat Found**\n\nPlease make sure group's voice chat is enabled. If already enabled, please end it and start fresh voice chat again and if the problem continues, try /restart"
                )
        except TelegramServerError:
            raise AssistantErr(
                "**Telegram Server Error**\n\nTelegram is having some internal server problems, Please try playing again.\n\n If this problem keeps coming everytime, please end your voice chat and start fresh voice chat again."
            )
        await add_active_chat(chat_id)
        await mute_off(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
        if await is_autoend():
            counter[chat_id] = {}
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(
                    minutes=AUTO_END_TIME
                )

    async def pop_tracks(self, chat_id: int, count: int = 1) -> bool:
        """Drop tracks from the head of the queue, True if any are left."""
        check = db.get(chat_id)
        for _ in range(count):
            if not check:
                break
            popped = check.pop(0)
            if config.AUTO_DOWNLOADS_CLEAR == str(True):
                await auto_clean(popped)
        return bool(check)

    async def change_stream(self, client, chat_id):
        async with self.chat_lock(chat_id):
            loop = await get_loop(chat_id)
            if loop:
                await set_loop(chat_id, loop - 1)
            else:
                await self.pop_tracks(chat_id)
            if not db.get(chat_id):
                await _clear_(chat_id)
                try:
                    await client.leave_call(chat_id)
                except Exception:
                    pass
                return
            await self.play_queued(chat_id, client)

    async def play_queued(
        self, chat_id: int, assistant: PyTgCalls = None
    ) -> bool:
        """Stream the track at the head of the queue and announce it.

        The caller must hold chat_lock(chat_id). Returns False when the track
        could not be started; the chat has been told why in that case.
        """
        check = db[chat_id]
        track = check[0]
        track["played"] = 0
        queued = track["file"]
        videoid = track["vidid"]
        user = track["by"]
        original_chat_id = track["chat_id"]
        video = str(track["streamtype"]) == "video"
        _ = get_string(await get_lang(original_chat_id))
        mystic = None
        if "live_" in queued:
            n, link = await YouTube.video(videoid, True)
            if n == 0:
                await app.send_message(
                    original_chat_id,
                    _["admin_11"].format(track["title"].title()),
                )
                return False
        elif "vid_" in queued:
            mystic = await app.send_message(
                original_chat_id, _["call_10"]
            )
            try:
                link, _direct = await YouTube.download(
                    videoid, mystic, videoid=True, video=video
                )
            except Exception:
                await mystic.edit_text(
                    _["call_9"],
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
                return False
        elif "index_" in queued:
            link = videoid
        else:
            link = queued
        # /stop may have cleared the queue while the track was being fetched
        if db.get(chat_id) is not check or not check or check[0] is not track:
            if mystic:
                await mystic.delete()
            return False
        if assistant is None:
            assistant = await group_assistant(self, chat_id)
        try:
            await assistant.play(
                chat_id,
                await self.media_stream(chat_id, link, video),
                config=call_config,
            )
        except Exception:
            if mystic:
                await mystic.edit_text(_["call_9"])
            else:
                await app.send_message(original_chat_id, _["call_9"])
            return False
        markup = "tg"
        if "index_" in queued:
            photo = config.STREAM_IMG_URL
            caption = _["stream_2"].format(user)
        elif videoid in ("telegram", "soundcloud"):
            if videoid == "soundcloud":
                photo = config.SOUNCLOUD_IMG_URL
            elif video:
                photo = config.TELEGRAM_VIDEO_URL
            else:
                photo = config.TELEGRAM_AUDIO_URL
            caption = _["stream_3"].format(
                track["title"].title(), track["dur"], user
            )
        else:
            photo = await gen_thumb(videoid)
            caption = _["stream_1"].format(
                user, f"https://t.me/{app.username}?start=info_{videoid}"
            )
            if "live_" not in queued:
                markup = "stream"
        buttons = (
            stream_markup(_, videoid, chat_id)
            if markup == "stream"
            else telegram_markup(_, chat_id)
        )
        if mystic:
            await mystic.delete()
        track["mystic"] = await app.send_photo(
            original_chat_id,
            photo=photo,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        track["markup"] = markup
        return True

    async def ping(self):
        pings = []
        if config.STRING1:
            pings.append(self.one.ping)
        if config.STRING2:
            pings.append(self.two.ping)
        if config.STRING3:
            pings.append(self.three.ping)
        if config.STRING4:
            pings.append(self.four.ping)
        if config.STRING5:
            pings.append(self.five.ping)
        return str(round(sum(pings) / len(pings), 3))

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Client\n")
        if config.STRING1:
            await self.one.start()
        if config.STRING2:
            await self.two.start()
        if config.STRING3:
            await self.three.start()
        if config.STRING4:
            await self.four.start()
        if config.STRING5:
            await self.five.start()

    async def decorators(self):
        services_filter = call_filters.chat_update(
            ChatUpdate.Status.KICKED
            | ChatUpdate.Status.CLOSED_VOICE_CHAT
            | ChatUpdate.Status.LEFT_GROUP
        )
        stream_end_filter = call_filters.stream_end(
            StreamEnded.Type.AUDIO
        )
        participants_filter = call_filters.call_participant(
            GroupCallParticipant.Action.JOINED
            | GroupCallParticipant.Action.LEFT
        )

        @self.one.on_update(services_filter)
        @self.two.on_update(services_filter)
        @self.three.on_update(services_filter)
        @self.four.on_update(services_filter)
        @self.five.on_update(services_filter)
        async def stream_services_handler(_, update: ChatUpdate):
            await self.stop_stream(update.chat_id)

        @self.one.on_update(stream_end_filter)
        @self.two.on_update(stream_end_filter)
        @self.three.on_update(stream_end_filter)
        @self.four.on_update(stream_end_filter)
        @self.five.on_update(stream_end_filter)
        async def stream_end_handler1(client, update: StreamEnded):
            await self.change_stream(client, update.chat_id)

        @self.one.on_update(participants_filter)
        @self.two.on_update(participants_filter)
        @self.three.on_update(participants_filter)
        @self.four.on_update(participants_filter)
        @self.five.on_update(participants_filter)
        async def participants_change_handler(
            client, update: UpdatedGroupCallParticipant
        ):
            chat_id = update.chat_id
            users = counter.get(chat_id)
            if not users:
                try:
                    got = len(await client.get_participants(chat_id))
                except Exception:
                    return
                counter[chat_id] = got
                if got == 1:
                    autoend[chat_id] = datetime.now() + timedelta(
                        minutes=AUTO_END_TIME
                    )
                    return
                autoend[chat_id] = {}
            else:
                final = (
                    users + 1
                    if update.action == GroupCallParticipant.Action.JOINED
                    else users - 1
                )
                counter[chat_id] = final
                if final == 1:
                    autoend[chat_id] = datetime.now() + timedelta(
                        minutes=AUTO_END_TIME
                    )
                    return
                autoend[chat_id] = {}


Yukki = Call()
