# hydownloader
# Copyright (C) 2021-2022  thatfuckingbird

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Logging functions. This module must not depend on the hydownloader database!
"""

import logging
import logging.handlers
import os
from typing import Optional, NoReturn

_inited = False
_log = logging.getLogger(__name__)
_fileHandler = None

def init(path: str, debug: bool) -> None:
    global _log, _inited, _fileHandler
    fmt = '%(levelname)s %(asctime)s %(message)s'

    streamHandler = logging.StreamHandler()
    logdir = path+"/logs"
    if not os.path.isdir(logdir):
        try:
            os.makedirs(logdir)
        except:
            print(f"Could not create log folder at {logdir}")
            raise
    _fileHandler = logging.handlers.RotatingFileHandler(logdir+"/daemon.txt", backupCount=128, encoding='utf-8')
    streamHandler.setFormatter(logging.Formatter(fmt))
    _fileHandler.setFormatter(logging.Formatter(fmt))

    _log.addHandler(streamHandler)
    _log.addHandler(_fileHandler)
    _log.setLevel(logging.DEBUG if debug else logging.INFO)

    _inited = True

def check_init():
    if not _inited:
        raise RuntimeError("Logging used but not initialized")

def warning(category: str, msg: str, exc_info: Optional[Exception] = None) -> None:
    check_init()
    _log.warning(f"[{category}] {msg}", exc_info = exc_info)

def info(category: str, msg: str, exc_info: Optional[Exception] = None) -> None:
    check_init()
    _log.info(f"[{category}] {msg}", exc_info = exc_info)

def error(category: str, msg: str, exc_info: Optional[Exception] = None) -> None:
    check_init()
    _log.error(f"[{category}] {msg}", exc_info = exc_info)

def fatal(category: str, msg: str, exc_info: Optional[Exception] = None) -> NoReturn:
    error(category, msg, exc_info)
    raise RuntimeError(msg)

def debug(category: str, msg: str, exc_info: Optional[Exception] = None) -> None:
    check_init()
    _log.debug(f"[{category}] {msg}", exc_info = exc_info)

def rotate() -> None:
    check_init()
    _fileHandler.doRollover()
