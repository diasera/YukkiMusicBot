#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import time


class Cooldown:
    """Per-key cooldown that forgets expired keys, so it never grows without bound."""

    def __init__(self, seconds: float, max_size: int = 1000):
        self.seconds = seconds
        self.max_size = max_size
        self._until = {}

    def hit(self, key) -> float:
        """Start the cooldown for key and return 0, or return the seconds left."""
        if self.seconds <= 0:
            return 0
        now = time.monotonic()
        until = self._until.get(key, 0)
        if until > now:
            return until - now
        self._until[key] = now + self.seconds
        if len(self._until) > self.max_size:
            self._until = {
                k: v for k, v in self._until.items() if v > now
            }
        return 0


def trim_oldest(store: dict, limit: int, keep=None):
    """Drop the oldest entries of store until it holds at most limit entries.

    Dicts keep insertion order, so the first keys are the oldest ones.
    Entries for which keep(value) is true are never dropped.
    """
    if len(store) <= limit:
        return
    for key in list(store):
        if len(store) <= limit:
            break
        if keep and keep(store[key]):
            continue
        del store[key]
