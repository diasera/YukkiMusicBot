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

from YukkiMusic.logging import LOGGER

# The event loop only keeps weak references to tasks, so background tasks are
# held here until they finish.
_running = set()


def create_task(coro, name: str = None) -> asyncio.Task:
    task = asyncio.create_task(coro, name=name)
    _running.add(task)
    task.add_done_callback(_on_done)
    return task


def _on_done(task: asyncio.Task):
    _running.discard(task)
    if not task.cancelled() and task.exception() is not None:
        LOGGER(__name__).error(
            f"Background task {task.get_name()} failed",
            exc_info=task.exception(),
        )
