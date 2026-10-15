#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import sys

from pymongo import AsyncMongoClient, MongoClient

import config

from ..logging import LOGGER

if config.MONGO_DB_URI is None:
    LOGGER(__name__).error(
        "No MONGO DB URL found.. Please set MONGO_DB_URI (or MONGO_URL) in your vars."
    )
    sys.exit()

_mongo_async_ = AsyncMongoClient(config.MONGO_DB_URI)
_mongo_sync_ = MongoClient(config.MONGO_DB_URI)
mongodb = _mongo_async_.Yukki
pymongodb = _mongo_sync_.Yukki
