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
import re

import spotipy
from py_yt import VideosSearch
from spotipy.oauth2 import SpotifyClientCredentials

import config


class SpotifyAPI:
    def __init__(self):
        self.regex = r"^(https:\/\/open.spotify.com\/)(.*)$"
        self.client_id = config.SPOTIFY_CLIENT_ID
        self.client_secret = config.SPOTIFY_CLIENT_SECRET
        if config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
            self.client_credentials_manager = (
                SpotifyClientCredentials(
                    self.client_id, self.client_secret
                )
            )
            self.spotify = spotipy.Spotify(
                client_credentials_manager=self.client_credentials_manager
            )
        else:
            self.spotify = None
        self._lock = asyncio.Lock()

    async def _call(self, method, *args):
        # spotipy is synchronous: run it in a thread so the bot keeps
        # responding, one request at a time as it always was.
        async with self._lock:
            return await asyncio.to_thread(method, *args)

    async def valid(self, link: str):
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def track(self, link: str):
        track = await self._call(self.spotify.track, link)
        info = track["name"]
        for artist in track["artists"]:
            fetched = f' {artist["name"]}'
            if "Various Artists" not in fetched:
                info += fetched
        results = VideosSearch(info, limit=1)
        for result in (await results.next())["result"]:
            ytlink = result["link"]
            title = result["title"]
            vidid = result["id"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": ytlink,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def playlist(self, url):
        playlist = await self._call(self.spotify.playlist, url)
        playlist_id = playlist["id"]
        results = []
        for item in playlist["tracks"]["items"]:
            music_track = item["track"]
            info = music_track["name"]
            for artist in music_track["artists"]:
                fetched = f' {artist["name"]}'
                if "Various Artists" not in fetched:
                    info += fetched
            results.append(info)
        return results, playlist_id

    async def album(self, url):
        album = await self._call(self.spotify.album, url)
        album_id = album["id"]
        results = []
        for item in album["tracks"]["items"]:
            info = item["name"]
            for artist in item["artists"]:
                fetched = f' {artist["name"]}'
                if "Various Artists" not in fetched:
                    info += fetched
            results.append(info)

        return (
            results,
            album_id,
        )

    async def artist(self, url):
        artistinfo = await self._call(self.spotify.artist, url)
        artist_id = artistinfo["id"]
        results = []
        artisttoptracks = await self._call(
            self.spotify.artist_top_tracks, url
        )
        for item in artisttoptracks["tracks"]:
            info = item["name"]
            for artist in item["artists"]:
                fetched = f' {artist["name"]}'
                if "Various Artists" not in fetched:
                    info += fetched
            results.append(info)

        return results, artist_id
