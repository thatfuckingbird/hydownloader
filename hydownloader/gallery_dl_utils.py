# hydownloader
# Copyright (C) 2021  thatfuckingbird

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
This file contains the functions that directly call gallery-dl, and various related helpers.
"""

import subprocess
import os
import sqlite3
from typing import Optional
from gallery_dl import extractor
from hydownloader import db, uri_normalizer, urls

_anchor_conn = None

def downloader_for_url(url: str) -> str:
    """
    Returns the name of the downloader that gallery-dl would use for the given URL.
    Returns an empty string if gallery-dl does not recognize the URL.
    """
    u = uri_normalizer.normalizes(url)
    if match := extractor.find(u):
        return match.category
    return ''

def check_db_for_anchor(anchor_pattern: str) -> bool:
    """
    Checks whether the given SQL LIKE-pattern is present in the anchor database.
    """
    global _anchor_conn
    if not _anchor_conn:
        _anchor_conn = sqlite3.connect(db.get_rootpath()+"/anchor.db", check_same_thread=False, timeout=24*60*60)
        _anchor_conn.row_factory = sqlite3.Row
    c = _anchor_conn.cursor()
    c.execute('select entry from archive where entry like ?', (anchor_pattern,))
    return len(c.fetchall()) > 0

def check_anchor_for_url(url: str) -> bool:
    """
    Checks whether the given file(s) represented by this URL are present
    in the anchor database.
    """
    u = uri_normalizer.normalizes(url)
    patterns = urls.anchor_patterns_from_url(u)
    for pattern in patterns:
        if check_db_for_anchor(pattern): return True
    return False

def append_file_contents(from_file: str, to_file: str) -> None:
    """
    Appends the contents of a file to another.
    Does nothing if the source file doesn't exist.
    """
    if os.path.isfile(from_file):
        to_f = open(to_file, 'a')
        text = open(from_file, 'r').read()
        if text and not text.endswith('\n'): text += '\n'
        to_f.write(text)
        to_f.close()

def run_gallery_dl_with_custom_args(args: list[str], capture_output: bool = False) -> subprocess.CompletedProcess:
    """
    This function runs gallery-dl with the given arguments in the current hydownloader environment.
    Some arguments beyond the ones passed in by the caller will be added (these are needed to make
    gallery-dl use the current hydownloader environment and conventions).
    """
    run_args = [str(db.get_conf('gallery-dl.executable'))]
    run_args += ['--ignore-config']
    run_args += ['--verbose']
    if os.path.isfile(db.get_rootpath() + "/gallery-dl-config.json"):
        run_args += ["-c", db.get_rootpath() + "/gallery-dl-config.json"]
    if os.path.isfile(db.get_rootpath() + "/gallery-dl-user-config.json"):
        run_args += ["-c", db.get_rootpath() + "/gallery-dl-user-config.json"]
    run_args += args
    result = subprocess.run(run_args, capture_output = capture_output, text = capture_output, check = False)
    return result

def run_gallery_dl(url: str, subscription_mode: bool, ignore_anchor: bool, metadata_only: bool, log_file: str, console_output_file: str, unsupported_urls_file: str, overwrite_existing: bool, filter_: Optional[str] = None, chapter_filter: Optional[str] = None, abort_after: Optional[int] = None, test_mode: bool = False, old_log_file: Optional[str] = None, old_unsupported_urls_file: Optional[str] = None, max_file_count: Optional[int] = None) -> str:
    """
    Downloads a URL with gallery-dl using the current hydownloader environment.
    """
    run_args = [str(db.get_conf('gallery-dl.executable'))]
    run_args += ['--ignore-config']
    run_args += ['--verbose']
    if os.path.isfile(db.get_rootpath() + "/gallery-dl-config.json"):
        run_args += ["-c", db.get_rootpath() + "/gallery-dl-config.json"]
    if os.path.isfile(db.get_rootpath() + "/gallery-dl-user-config.json"):
        run_args += ["-c", db.get_rootpath() + "/gallery-dl-user-config.json"]
    run_args += ['--cookies', db.get_rootpath()+'/cookies.txt']
    if not test_mode:
        if override := str(db.get_conf("gallery-dl.data-override")):
            run_args += ['--dest', override+'/gallery-dl']
        else:
            run_args += ['--dest', db.get_rootpath()+'/data/gallery-dl']
    else:
        run_args += ['--dest', db.get_rootpath()+'/test/data/gallery-dl']
    run_args += ['--write-metadata']
    if metadata_only:
        run_args += ['--no-download']
    if old_log_file: append_file_contents(log_file, old_log_file)
    run_args += ['--write-log', log_file]
    if old_unsupported_urls_file: append_file_contents(unsupported_urls_file, old_unsupported_urls_file)
    run_args += ['--write-unsupported', unsupported_urls_file]
    if overwrite_existing:
        run_args += ['--no-skip']
    if not ignore_anchor:
        if not test_mode:
            if override := str(db.get_conf("gallery-dl.archive-override")):
                run_args += ["--download-archive", override]
            else:
                run_args += ["--download-archive", db.get_rootpath()+'/anchor.db']
        else:
            run_args += ["--download-archive", db.get_rootpath()+'/test/anchor.db']
    if filter_:
        run_args += ['--filter', filter_]
    if chapter_filter:
        run_args += ['--chapter-filter', chapter_filter]
    if subscription_mode and abort_after:
        run_args += ['-A', f'{abort_after}']
    if max_file_count:
        run_args += ['-o', f'image-range="1-{max_file_count}"']

    run_args += ['-o', 'cache.file='+db.get_rootpath()+'/gallery-dl-cache.db']
    run_args += [url]

    console_out = open(console_output_file, 'a')
    console_out.write('\n')
    result = subprocess.run(run_args, text = True, stdout = console_out, stderr = console_out, check = False)
    console_out.close()

    return check_return_code(result.returncode)

def check_return_code(code: int) -> str:
    """
    Converts gallery-dl return codes to textual error descriptions.
    """
    errors = []
    if code & 1: errors.append("unspecified error")
    if code & 2: errors.append("cmdline arguments")
    if code & 4: errors.append("http error")
    if code & 8: errors.append("not found / 404")
    if code & 16: errors.append("auth / login")
    if code & 32: errors.append("format or filter")
    if code & 64: errors.append("no extractor")
    if code & 128: errors.append("os error")
    return ", ".join(errors)
