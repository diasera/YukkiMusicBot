#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
# Copyright (C) 2021-present by diasera@Github, < https://github.com/diasera >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram.types import InlineKeyboardMarkup


# Replacement for pykeyboard.InlineKeyboard, which depends on the official
# pyrogram package and would overwrite kurigram when installed.
class InlineKeyboard(InlineKeyboardMarkup):
    def __init__(self, row_width=3):
        self.inline_keyboard = list()
        super().__init__(inline_keyboard=self.inline_keyboard)
        self.row_width = row_width

    def add(self, *args):
        self.inline_keyboard = [
            list(args[i : i + self.row_width])
            for i in range(0, len(args), self.row_width)
        ]

    def row(self, *args):
        self.inline_keyboard.append(list(args))
