#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
# Copyright (C) 2021-present by diasera@Github, < https://github.com/diasera >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.
#

import glob
import os
from os.path import dirname, isfile, relpath, splitext


def __list_all_modules():
    work_dir = dirname(__file__)
    mod_paths = glob.glob(os.path.join(work_dir, "*", "*.py"))

    # os.sep keeps module names valid on Windows ("\") as well as Linux ("/")
    all_modules = [
        "." + splitext(relpath(f, work_dir))[0].replace(os.sep, ".")
        for f in mod_paths
        if isfile(f)
        and f.endswith(".py")
        and not f.endswith("__init__.py")
    ]

    return all_modules


ALL_MODULES = sorted(__list_all_modules())
__all__ = ALL_MODULES + ["ALL_MODULES"]
