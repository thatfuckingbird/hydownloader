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

import sqlite3
import sys
import os
import os.path
import json
import time
import urllib.parse
import datetime
import threading
from typing import Optional, Union
from hydownloader import log, uri_normalizer, __version__, constants as C

_conn_lock = threading.Lock()
_conn: dict[int, sqlite3.Connection] = {}
_shared_conn_lock = threading.Lock()
_update_lock = threading.Lock()
_shared_conn: dict[int, sqlite3.Connection] = {}
_closed_threads_lock = threading.Lock()
_closed_threads: set[int] = set()
_path: str = None # type: ignore
_config: dict = None # type: ignore
_inited = False

def _shared_db_path() -> str:
    if _config["shared-db-override"]:
        return _config["shared-db-override"]
    return _path+"/hydownloader.shared.db"

def get_conn() -> sqlite3.Connection:
    global _conn
    thread_id = threading.get_ident()
    if not thread_id in _conn:
        with _conn_lock:
            _conn[thread_id] = sqlite3.connect(_path+"/hydownloader.db", timeout=24*60*60)
            if get_conf('disable-wal', False, True):
                _conn[thread_id].cursor().execute('pragma journal_mode=delete')
            else:
                _conn[thread_id].cursor().execute('pragma journal_mode=wal')
            _conn[thread_id].row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            return _conn[thread_id]
    return _conn[thread_id]

def get_shared_conn() -> sqlite3.Connection:
    global _shared_conn
    thread_id = threading.get_ident()
    if not thread_id in _shared_conn:
        with _shared_conn_lock:
            _shared_conn[thread_id] = sqlite3.connect(_shared_db_path(), timeout=24*60*60)
            if get_conf('disable-wal', False, True):
                _shared_conn[thread_id].cursor().execute('pragma journal_mode=delete')
            else:
                _shared_conn[thread_id].cursor().execute('pragma journal_mode=wal')
            _shared_conn[thread_id].row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            return _shared_conn[thread_id]
    return _shared_conn[thread_id]

def upsert_dict(table: str, d: dict, no_commit: bool = False) -> None:
    keys = d.keys()
    column_names = ",".join(keys)
    placeholders = ",".join(["?"]*len(keys))
    update_part = ",".join(f"{key}=?" for key in keys if key not in ("id", "rowid"))
    values = []
    c = get_conn().cursor()
    update = False
    update_with_rowid = False
    if "id" in d:
        c.execute(f"select id from {table} where id = ?", (d["id"],))
        if c.fetchone(): update = True
    elif "rowid" in d:
        c.execute(f"select rowid from {table} where rowid = ?", (d["rowid"],))
        if c.fetchone(): update_with_rowid = True
    if update:
        query = f"update {table} set {update_part} where id = ?"
        values = [d[key] for key in keys if key != "id"] + [d["id"]]
    elif update_with_rowid:
        query = f"update {table} set {update_part} where rowid = ?"
        values = [d[key] for key in keys if key != "rowid"] + [d["rowid"]]
    else:
        query = f"insert into {table} ({column_names}) values ({placeholders})"
        values = [d[key] for key in keys]
    c.execute(query, values)
    if not no_commit: get_conn().commit()

def validate_json_syntax(path: str) -> None:
    files_to_check = ["gallery-dl-config.json", "gallery-dl-user-config.json", "hydownloader-config.json", "hydownloader-import-jobs.json"]
    for file in files_to_check:
        try:
            log.info("hydownloader", f"Checking file for syntax errors: {file}")
            json.load(open(path+"/"+file, 'r'))
        except json.decoder.JSONDecodeError as e:
            log.fatal("hydownloader", f"The file {file} contains invalid JSON syntax.", e)

def init(path : str) -> None:
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ["PYTHONIOENCODING"] = "utf-8"
    global _inited, _path, _config
    _path = path
    if not os.path.isdir(path):
        log.info("hydownloader", f"Initializing new database folder at {path}")
        os.makedirs(path)
    if not os.path.isdir(path + "/logs"):
        os.makedirs(path + "/logs")
    if not os.path.isdir(path + "/logs"):
        os.makedirs(path + "/data")
    if not os.path.isdir(path + "/temp"):
        os.makedirs(path + "/temp")
    needs_db_init = False
    if not os.path.isfile(path+"/hydownloader.db"):
        needs_db_init = True
    if not os.path.isfile(path+"/gallery-dl-config.json"):
        gdl_cfg = open(path+"/gallery-dl-config.json", 'w', encoding='utf-8')
        gdl_cfg.write(C.DEFAULT_GALLERY_DL_CONFIG)
        gdl_cfg.close()
    if not os.path.isfile(path+"/gallery-dl-user-config.json"):
        gdl_cfg = open(path+"/gallery-dl-user-config.json", 'w', encoding='utf-8')
        gdl_cfg.write(C.DEFAULT_GALLERY_DL_USER_CONFIG)
        gdl_cfg.close()
    if not os.path.isfile(path+"/hydownloader-config.json"):
        hydl_cfg = open(path+"/hydownloader-config.json", 'w', encoding='utf-8')
        hydl_cfg.write(json.dumps(C.DEFAULT_CONFIG, indent=4))
        hydl_cfg.close()
    if not os.path.isfile(path+"/hydownloader-import-jobs.json"):
        hydl_cfg = open(path+"/hydownloader-import-jobs.json", 'w', encoding='utf-8')
        hydl_cfg.write(C.DEFAULT_IMPORT_JOBS)
        hydl_cfg.close()
    if not os.path.isfile(path+"/cookies.txt"):
        open(path+"/cookies.txt", "w", encoding="utf-8").close()
    _config = json.load(open(path+"/hydownloader-config.json", "r", encoding="utf-8-sig"))
    get_conn()
    if needs_db_init: create_db()

    need_shared_db_init = not os.path.isfile(_shared_db_path())
    get_shared_conn()
    if need_shared_db_init: create_shared_db()

    validate_json_syntax(path)
    check_and_update_db()

    _inited = True

def create_db() -> None:
    c = get_conn().cursor()
    c.execute(C.CREATE_SUBS_STATEMENT)
    c.execute(C.CREATE_URL_QUEUE_STATEMENT)
    c.execute(C.CREATE_ADDITIONAL_DATA_STATEMENT)
    c.execute(C.CREATE_SINGLE_URL_INDEX_STATEMENT)
    c.execute(C.CREATE_KNOWN_URLS_STATEMENT)
    c.execute(C.CREATE_LOG_FILES_TO_PARSE_STATEMENT)
    c.execute(C.CREATE_KEYWORD_INDEX_STATEMENT)
    c.execute(C.CREATE_VERSION_STATEMENT)
    c.execute(C.CREATE_SUBSCRIPTION_CHECKS_STATEMENT)
    c.execute(C.CREATE_KNOWN_URL_INDEX_STATEMENT)
    c.execute(C.CREATE_FILE_INDEX_STATEMENT)
    c.execute(C.CREATE_URL_ID_INDEX_STATEMENT)
    c.execute(C.CREATE_SUBSCRIPTION_ID_INDEX_STATEMENT)
    c.execute(C.CREATE_MISSED_SUBSCRIPTION_CHECKS_STATEMENT)
    c.execute(C.CREATE_REVERSE_LOOKUP_JOBS_STATEMENT)
    c.execute('insert into version(version) values (?)', (__version__,))
    get_conn().commit()

def create_shared_db() -> None:
    c = get_shared_conn().cursor()
    c.execute(C.SHARED_CREATE_KNOWN_URLS_STATEMENT)
    c.execute(C.SHARED_CREATE_KNOWN_URL_INDEX_STATEMENT)
    c.execute(C.SHARED_CREATE_IMPORTED_FILES_STATEMENT)
    c.execute(C.SHARED_CREATE_IMPORTED_FILE_INDEX_STATEMENT)
    get_shared_conn().commit()

def get_rootpath() -> str:
    check_init()
    return _path

def get_datapath() -> str:
    check_init()
    if override := str(get_conf("gallery-dl.data-override")):
        return override
    return get_rootpath()+'/data'

def associate_additional_data(filename: str, subscription_id: Optional[int] = None, url_id: Optional[int] = None, no_commit: bool = False) -> None:
    check_init()
    if subscription_id is None and url_id is None: raise ValueError("associate_additional_data: both IDs cannot be None")
    filename = os.path.relpath(filename, get_datapath())
    c = get_conn().cursor()
    data = None
    already_saved = None
    if subscription_id is not None:
        c.execute('select additional_data from subscriptions where id = ?', (subscription_id,))
        rows = c.fetchall()
        if len(rows): data = rows[0]['additional_data']
        c.execute('select * from additional_data where file = ? and subscription_id = ? and data = ? limit 1', (filename, subscription_id, data))
        already_saved = c.fetchone()
    else:
        c.execute('select additional_data from single_url_queue where id = ?', (url_id,))
        rows = c.fetchall()
        if len(rows): data = rows[0]['additional_data']
        c.execute('select * from additional_data where file = ? and url_id = ? and data = ? limit 1', (filename, url_id, data))
        already_saved = c.fetchone()
    if not already_saved:
        c.execute('insert into additional_data(file, data, subscription_id, url_id, time_added) values (?,?,?,?,?)', (filename, data, subscription_id, url_id, time.time()))
    if not no_commit: get_conn().commit()

def get_last_files_for_url(url_id: int) -> list[str]:
    check_init()
    result = []
    c = get_conn().cursor()
    c.execute('select file from additional_data where url_id = ? order by time_added desc limit 5', (url_id,))
    for item in c.fetchall():
        result.append(get_datapath()+"/"+item['file'])
    return result

def get_last_files_for_sub(sub_id: int) -> list[str]:
    check_init()
    result = []
    c = get_conn().cursor()
    c.execute('select file from additional_data where subscription_id = ? order by time_added desc limit 5', (sub_id,))
    for item in c.fetchall():
        result.append(get_datapath()+"/"+item['file'])
    return result

def sync() -> None:
    check_init()
    get_conn().commit()
    get_shared_conn().commit()

def check_init() -> None:
    if not _inited:
        log.fatal("hydownloader", "Database used but not initalized")

def get_db_version() -> str:
    c = get_conn().cursor()
    c.execute('select version from version')
    v = c.fetchall()
    if len(v) != 1:
        log.fatal("hydownloader", "Invalid version table in hydownloader database")
    return v[0]['version']

def check_and_update_db() -> None:
    def write_new_config(names: list[str]):
        for name in names:
            if name == "gallery-dl-user-config.json":
                with open(_path+f"/{name}.NEW", 'w', encoding='utf-8') as f:
                    f.write(C.DEFAULT_GALLERY_DL_USER_CONFIG)
            elif name == "gallery-dl-config.json":
                with open(_path+f"/{name}.NEW", 'w', encoding='utf-8') as f:
                    f.write(C.DEFAULT_GALLERY_DL_CONFIG)
            elif name == "hydownloader-import-jobs.json":
                with open(_path+f"/{name}.NEW", 'w', encoding='utf-8') as f:
                    f.write(C.DEFAULT_IMPORT_JOBS)
            else:
                continue
            log.info("hydownloader", f"Written {name}.NEW with default content")
    with _update_lock:
        while True:
            version = get_db_version()
            if version == __version__:
                break
            elif version == "0.1.0": # 0.1.0 -> 0.2.0
                log.info("hydownloader", "Starting database upgrade to version 0.2.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Adding gallerydl_config to subscriptions...")
                    cur.execute('alter table "subscriptions" add "gallerydl_config" text')
                    log.info("hydownloader", "Adding gallerydl_config to single URLs...")
                    cur.execute('alter table "single_url_queue" add "gallerydl_config" text')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.2.0\'')
                log.info("hydownloader", "Upgraded database to version 0.2.0")
            elif version == "0.2.0": # 0.2.0 -> 0.3.0
                log.info("hydownloader", "Starting database upgrade to version 0.3.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["gallery-dl-user-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-user-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The `\"external\": true` config option was added in the `\"extractor\"` group.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Enabling this option will make gallery-dl follow external links on some sites (usually embeds, or in the case of danbooru, the source link if the image is not accessible or was deleted).")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Edit your gallery-dl-user-config.json accordingly if you want to enable this option. This change is optional.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.3.0\'')
                log.info("hydownloader", "Upgraded database to version 0.3.0")
            elif version == "0.3.0": # 0.3.0 -> 0.4.0
                log.info("hydownloader", "Starting database upgrade to version 0.4.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["gallery-dl-user-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-user-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The `\"fallback\": false` config option was added for twitter.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! This disables downloading secondary, lower resolution ('fallback') versions of images if the full resolution download fails.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Edit your gallery-dl-user-config.json accordingly if you want to enable this option. This change is optional.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.4.0\'')
                log.info("hydownloader", "Upgraded database to version 0.4.0")
            elif version == "0.4.0": # 0.4.0 -> 0.5.0
                log.info("hydownloader", "Starting database upgrade to version 0.5.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["gallery-dl-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A \"downloader\" section was added, containing the `\"progress\": null` option.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! This disables the newly (in version 1.19.0) introduced progress indicator feature of gallery-dl that could interfere with log file parsing.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Edit your gallery-dl-config.json accordingly. This change is NOT optional.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.5.0\'')
                log.info("hydownloader", "Upgraded database to version 0.5.0")
            elif version == "0.5.0": # 0.5.0 -> 0.6.0
                log.info("hydownloader", "Starting database upgrade to version 0.6.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["gallery-dl-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The \"image\" subsection was added to the \"twitter\" section, containing configuration for properly handling direct twitter image links.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Without this configuration, trying to download direct image links from twitter (using the twimg.com domain) will error.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Keep in mind that even though after this change downloading direct image links will work, it will produce less metadata than downloading a tweet URL, so if possible, always prefer downloading tweets instead of direct image links.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Edit your gallery-dl-config.json accordingly. This change is NOT optional.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.6.0\'')
                log.info("hydownloader", "Upgraded database to version 0.6.0")
            elif version == "0.6.0": # 0.6.0 -> 0.7.0
                log.info("hydownloader", "Starting database upgrade to version 0.7.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.7.0\'')
                log.info("hydownloader", "Upgraded database to version 0.7.0")
            elif version == "0.7.0": # 0.7.0 -> 0.8.0
                log.info("hydownloader", "Starting database upgrade to version 0.8.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Creating missed_subscription_checks table...")
                    cur.execute(C.CREATE_MISSED_SUBSCRIPTION_CHECKS_STATEMENT)
                    write_new_config(["gallery-dl-user-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-user-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The \"comments\" option was added and set to true in the \"kemonoparty\" section, so that comments are also saved into the metadata when downloading from kemono.party.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Edit your gallery-dl-user-config.json accordingly if you want to enable this option. This change is optional.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The importer now uses forward slashes in filepaths on all platforms.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Windows users who changed paths in the importer configuration to backslashes will likely need to change them back to forward slashes like in the default configuration.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.8.0\'')
                log.info("hydownloader", "Upgraded database to version 0.8.0")
            elif version == "0.8.0": # 0.8.0 -> 0.9.0
                log.info("hydownloader", "Starting database upgrade to version 0.9.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["gallery-dl-user-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-user-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The \"dms\" option was added and set to true in the \"kemonoparty\" section, so that DMs are also saved into the metadata when downloading from kemono.party.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Edit your gallery-dl-user-config.json accordingly if you want to enable this option. This change is optional.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.9.0\'')
                log.info("hydownloader", "Upgraded database to version 0.9.0")
            elif version == "0.9.0": # 0.9.0 -> 0.10.0
                log.rotate()
                log.info("hydownloader", "Starting database upgrade to version 0.10.0")
                log.info("hydownloader", "The daemon log file has been rotated due to the switch to UTF-8 encoding")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["hydownloader-import-jobs.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of hydownloader-import-jobs.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The \"path.startswith\" function was replaced with \"pstartswith\". This should hopefully resolve all path matching issues in the importer on Windows.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! You can do this replacement yourself by replacing all instances of \"path.startswith(\" with \"pstartswith(path, \" (without the outer double quotes) in the importer job config JSON file.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! This change is optional but highly recommended if you are on Windows.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.10.0\'')
                log.info("hydownloader", "Upgraded database to version 0.10.0")
            elif version == "0.10.0": # 0.10.0 -> 0.11.0
                log.info("hydownloader", "Starting database upgrade to version 0.11.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.11.0\'')
                log.info("hydownloader", "Upgraded database to version 0.11.0")
            elif version == "0.11.0": # 0.11.0 -> 0.12.0
                log.info("hydownloader", "Starting database upgrade to version 0.12.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.12.0\'')
                log.info("hydownloader", "Upgraded database to version 0.12.0")
            elif version == "0.12.0": # 0.12.0 -> 0.13.0
                log.info("hydownloader", "Starting database upgrade to version 0.13.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.13.0\'')
                log.info("hydownloader", "Upgraded database to version 0.13.0")
            elif version == "0.13.0": # 0.13.0 -> 0.14.0
                log.info("hydownloader", "Starting database upgrade to version 0.14.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["gallery-dl-user-config.json", "gallery-dl-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-user-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The `\"-nostdin\"` flag was added to ffmpeg-args. This is to prevent some rare ffmpeg hangs.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Edit your gallery-dl-user-config.json accordingly if you want to apply this change. This change is optional, but recommended.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The `\"signals-ignore\": [\"SIGTTOU\", \"SIGTTIN\"]` top level config option was added. This is to prevent some rare ffmpeg hangs.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Edit your gallery-dl-config.json accordingly if you want to apply this change. This change is optional, but recommended.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! A file with the new default content, with name ending in .NEW, was created in your database directory to help with applying the changes.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.14.0\'')
                log.info("hydownloader", "Upgraded database to version 0.14.0")
            elif version == "0.14.0": # 0.14.0 -> 0.15.0
                log.info("hydownloader", "Starting database upgrade to version 0.15.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.15.0\'')
                log.info("hydownloader", "Upgraded database to version 0.15.0")
            elif version == "0.15.0": # 0.15.0 -> 0.16.0
                log.info("hydownloader", "Starting database upgrade to version 0.16.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.warning("hydownloader", "!!BREAKING CHANGE!! hydownloader now manages the value of the `\"url-metadata\"` configuration option (in order to store the subscription/URL ID in the name of the metadata key).")
                    log.warning("hydownloader", "!!BREAKING CHANGE!! The old key name was always \"gallerydl_file_url\". This is now either \"gallerydl_file_url_sub_ID\" or \"gallerydl_file_url_singleurl_ID\" where ID is the integer ID of the subscription/single URL.")
                    log.warning("hydownloader", "!!BREAKING CHANGE!! If you have any custom importer configuration or custom scripts that use this key, you have to adjust them. If you don't, then this change does not affect you.")
                    log.info("hydownloader", "Adding reverse_lookup_id to single_url_queue...")
                    cur.execute('alter table "single_url_queue" add "reverse_lookup_id" integer')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.16.0\'')
                log.info("hydownloader", "Upgraded database to version 0.16.0")
            elif version == "0.16.0": # 0.16.0 -> 0.17.0
                log.info("hydownloader", "Starting database upgrade to version 0.17.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Creating reverse_lookup_jobs table...")
                    cur.execute(C.CREATE_REVERSE_LOOKUP_JOBS_STATEMENT)
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.17.0\'')
                log.info("hydownloader", "Upgraded database to version 0.17.0")
            elif version == "0.17.0": # 0.17.0 -> 0.18.0
                log.info("hydownloader", "Starting database upgrade to version 0.18.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["hydownloader-import-jobs.json", "gallery-dl-user-config.json", "gallery-dl-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-user-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The \"duplicates\" key was added and set to true for \"kemonoparty\". This change is optional.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The \"syndication\" key was added and set to true for \"twitter\". This change is optional, but highly recommended because it is required to access age-gated tweets if not logged in to Twitter.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The value of the \"filename\" key was updated for \"kemonoparty\". This change is optional, but highly recommended because the old value generated too long filenames which sometimes caused download errors.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The \"rule34\" group was added. This change is optional, but highly recommended because it is needed to correctly handle downloads from rule34.xxx.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! See the newly written default configuration files (name ending in .NEW) in your database folder.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of hydownloader-import-jobs.json changed: rules for rule34.xxx were added.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! See the newly written default importer configuration file (name ending in .NEW) in your database folder.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.18.0\'')
                log.info("hydownloader", "Upgraded database to version 0.18.0")
            elif version == "0.18.0": # 0.18.0 -> 0.19.0
                log.info("hydownloader", "Starting database upgrade to version 0.19.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.19.0\'')
                log.info("hydownloader", "Upgraded database to version 0.19.0")
            elif version == "0.19.0": # 0.19.0 -> 0.20.0
                log.info("hydownloader", "Starting database upgrade to version 0.20.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    write_new_config(["hydownloader-import-jobs.json", "gallery-dl-user-config.json"])
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of gallery-dl-user-config.json changed.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The \"include\" key was added and set to \"avatar,background,artworks\" for \"pixiv\". This change is optional. Applying this change will cause background and artist profile images to be downloaded (in addition to artworks).")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! See the newly written default configuration file (name ending in .NEW) in your database folder.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The default content of hydownloader-import-jobs.json changed:")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! The URL generation rules for Newgrounds were updated. Newgrounds changed their URL format, so the old rule now produces invalid post URLs.")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! Fixes were made to the code of the \"gelbooru id\" tag rule and the URL rule that generates gelbooru post URLs (the format of the generated results did not change, but an integer->string type conversion of IDs was missing).")
                    log.warning("hydownloader", "!!MANUAL INTERVENTION REQUIRED!! See the newly written default importer configuration file (name ending in .NEW) in your database folder.")
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.20.0\'')
                log.info("hydownloader", "Upgraded database to version 0.20.0")
            elif version == "0.20.0": # 0.20.0 -> 0.21.0
                log.info("hydownloader", "Starting database upgrade to version 0.21.0")
                with sqlite3.connect(_path+"/hydownloader.db") as connection:
                    cur = connection.cursor()
                    cur.execute('begin exclusive transaction')
                    log.info("hydownloader", "Updating version number...")
                    cur.execute('update version set version = \'0.21.0\'')
                log.info("hydownloader", "Upgraded database to version 0.21.0")
            else:
                log.fatal("hydownloader", "Unsupported hydownloader database version found")

def get_due_subscriptions() -> list[dict]:
    check_init()
    c = get_conn().cursor()
    current_time = time.time()
    result = []
    # subs that had no errors (last check was successful or there was no check yet)
    result.extend(c.execute(
    """
        select * from subscriptions where
            paused <> 1 and
            (last_check = last_successful_check or last_check is null) and
            (max(last_check,ifnull(last_successful_check, 0)) + check_interval <= ? or last_check is null) and
            (max(last_check,ifnull(last_successful_check, 0)) + 60 <= ? or last_check is null)
        order by priority desc, ifnull(last_check, 0) asc
    """, (current_time, current_time)).fetchall())
    # subs with errors (last check != last successful check)
    result.extend(c.execute(
    """
        select * from subscriptions where
            paused <> 1 and
            last_check is not null and
            (last_check <> last_successful_check or last_successful_check is null) and
            max(last_check,ifnull(last_successful_check, 0)) + 60 <= ?
        order by priority desc, max(last_check,ifnull(last_successful_check, 0)) asc
    """, (current_time,)).fetchall())
    return result

def get_urls_to_download() -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.execute('select * from single_url_queue where status = -1 and paused <> 1 order by priority desc, time_added desc')
    return c.fetchall()

def add_or_update_urls(url_data: list[dict]) -> bool:
    check_init()
    for item in url_data:
        add = "id" not in item
        if add and not "url" in item: continue
        if add: item["time_added"] = time.time()
        if 'url' in item: item['url'] = uri_normalizer.normalizes(item['url'])
        if add:
            defaults = get_conf('url-defaults', True)
            if defaults:
                for key in defaults:
                    if not key in item: item[key] = defaults[key]
        upsert_dict("single_url_queue", item, no_commit = True)
        if add:
            log.info("hydownloader", f"Added URL: {item['url']}")
        else:
            log.info("hydownloader", f"Updated URL with ID {item['id']}")
    get_conn().commit()
    return True

def check_single_queue_for_url(url: str) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    url = uri_normalizer.normalizes(url)
    c.execute('select * from single_url_queue where url = ?', (url,))
    return c.fetchall()

def get_subscriptions_by_downloader_data(downloader: str, keywords: str) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.execute("select * from subscriptions where downloader = ? and keywords = ?", (downloader, keywords))
    results = c.fetchall()
    if not results: # if nothing found, try the unquoted version too
        c.execute("select * from subscriptions where downloader = ? and keywords = ?", (downloader, urllib.parse.unquote(keywords)))
        results = c.fetchall()
    return results

def get_additional_data_for_file(filepath: str) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.execute("select * from additional_data where file = ?", (filepath,))
    results = []
    # get the current additional_data field of related single URLs and subscriptions
    for entry in c.fetchall():
        results.append(entry)
        if entry['url_id']:
            for sub in get_subs_by_id([entry['subscription_id']]):
                if sub['additional_data']:
                    results.append({
                        'file': entry['file'],
                        'time_added': None,
                        'subscription_id': sub['id'],
                        'url_id': None,
                        'additional_data': sub['additional_data']
                    })
        if entry['subscription_id']:
            for url in get_queued_urls_by_id([entry['url_id']], True):
                if url['additional_data']:
                    results.append({
                        'file': entry['file'],
                        'time_added': None,
                        'subscription_id': None,
                        'url_id': url['id'],
                        'additional_data': url['additional_data']
                    })
    return results

def add_or_update_subscriptions(sub_data: list[dict]) -> bool:
    check_init()
    for item in sub_data:
        add = "id" not in item
        if add and not "keywords" in item: continue
        if add and not "downloader" in item: continue
        if add and not "additional_data" in item: item["additional_data"] = ""
        if add: item["time_created"] = time.time()
        if add:
            defaults_downloader = get_conf(f"subscription-defaults-{item['downloader']}", True)
            if defaults_downloader:
                for key in defaults_downloader:
                    if not key in item: item[key] = defaults_downloader[key]
            defaults_any = get_conf(f"subscription-defaults-any", True)
            if defaults_any:
                for key in defaults_any:
                    if not key in item: item[key] = defaults_any[key]
        upsert_dict("subscriptions", item, no_commit = True)
        if add:
            log.info("hydownloader", f"Added subscription: {item['keywords']} for downloader {item['downloader']}")
        else:
            log.info("hydownloader", f"Updated subscription with ID {item['id']}")
    get_conn().commit()
    return True

def add_or_update_subscription_checks(sub_data: list[dict]) -> bool:
    check_init()
    for item in sub_data:
        add = "rowid" not in item
        if add: item["time_created"] = time.time()
        upsert_dict("subscription_checks", item, no_commit = True)
        if add:
            log.info("hydownloader", f"Added subscription check entry: rowid {item['rowid']}")
        else:
            log.info("hydownloader", f"Updated subscription check entry with rowid {item['rowid']}")
    get_conn().commit()
    return True

def add_or_update_missed_subscription_checks(sub_data: list[dict]) -> bool:
    check_init()
    for item in sub_data:
        add = "rowid" not in item
        if add: item["time"] = time.time()
        upsert_dict("missed_subscription_checks", item, no_commit = True)
        if add:
            log.info("hydownloader", f"Added missed subscription check entry: rowid {item['rowid']}")
        else:
            log.info("hydownloader", f"Updated missed subscription check entry with rowid {item['rowid']}")
    get_conn().commit()
    return True

def add_subscription_check(subscription_id: int, new_files: int, already_seen_files: int, time_started: Union[float,int], time_finished: Union[float,int], status: str) -> None:
    check_init()
    c = get_conn().cursor()
    c.execute('insert into subscription_checks(subscription_id, new_files, already_seen_files, time_started, time_finished, status) values (?,?,?,?,?,?)', (subscription_id,new_files,already_seen_files,time_started,time_finished,status))
    get_conn().commit()

def add_missed_subscription_check(subscription_id: int, reason: int, data: Optional[str]) -> int:
    check_init()
    c = get_conn().cursor()
    c.execute('insert into missed_subscription_checks(subscription_id, reason, data, archived, time) values (?,?,?,?,?)', (subscription_id,reason,data,False,time.time()))
    get_conn().commit()
    return c.lastrowid

def get_subscription_checks(subscription_ids: list[int], archived: bool) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.arraysize = 1000
    if subscription_ids:
        if archived:
            c.execute(f'select rowid, * from subscription_checks where subscription_id in {"(" + ",".join(["?"]*len(subscription_ids)) + ")"} order by rowid asc', tuple(subscription_ids))
        else:
            c.execute(f'select rowid, * from subscription_checks where subscription_id in {"(" + ",".join(["?"]*len(subscription_ids)) + ")"} and archived <> 1 order by rowid asc', tuple(subscription_ids))
    else:
        if archived:
            c.execute('select rowid, * from subscription_checks order by rowid asc')
        else:
            c.execute('select rowid, * from subscription_checks where archived <> 1 order by rowid asc')
    return list(c.fetchall())

def get_missed_subscription_checks(subscription_ids: list[int], archived: bool) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.arraysize = 1000
    if subscription_ids:
        if archived:
            c.execute(f'select rowid, * from missed_subscription_checks where subscription_id in {"(" + ",".join(["?"]*len(subscription_ids)) + ")"} order by rowid asc', tuple(subscription_ids))
        else:
            c.execute(f'select rowid, * from missed_subscription_checks where subscription_id in {"(" + ",".join(["?"]*len(subscription_ids)) + ")"} and archived <> 1 order by rowid asc', tuple(subscription_ids))
    else:
        if archived:
            c.execute('select rowid, * from missed_subscription_checks order by rowid asc')
        else:
            c.execute('select rowid, * from missed_subscription_checks where archived <> 1 order by rowid asc')
    return list(c.fetchall())

def delete_urls(url_ids: list[int]) -> bool:
    check_init()
    c = get_conn().cursor()
    for i in url_ids:
        c.execute('delete from single_url_queue where id = ?', (i,))
    get_conn().commit()
    log.info("hydownloader", f"Deleted URLs with IDs: {', '.join(map(str, url_ids))}")
    return True

def delete_subscriptions(sub_ids: list[int]) -> bool:
    check_init()
    c = get_conn().cursor()
    for i in sub_ids:
        c.execute('delete from subscriptions where id = ?', (i,))
    get_conn().commit()
    log.info("hydownloader", f"Deleted subscriptions with IDs: {', '.join(map(str, sub_ids))}")
    return True

def delete_missed_subscription_check(rowid: int) -> None:
    check_init()
    c = get_conn().cursor()
    c.execute('delete from missed_subscription_checks where rowid = ?', (rowid,))
    get_conn().commit()

def get_subs_by_range(range_: Optional[tuple[int, int]] = None) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.arraysize = 1000
    if range_ is None:
        c.execute('select * from subscriptions order by id asc')
    else:
        c.execute('select * from subscriptions where id >= ? and id <= ? order by id asc', range_)
    return list(c.fetchall())

def get_subs_by_id(sub_ids: list[int]) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    result = []
    for i in sub_ids:
        c.execute('select * from subscriptions where id = ?', (i,))
        for row in c.fetchall():
            result.append(row)
    return result

def get_queued_urls_by_range(archived: bool, range_: Optional[tuple[int, int]] = None) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.arraysize = 1000
    if range_ is None:
        if archived:
            c.execute('select * from single_url_queue order by id asc')
        else:
            c.execute('select * from single_url_queue where archived <> 1 order by id asc')
    else:
        if archived:
            c.execute('select * from single_url_queue where id >= ? and id <= ? order by id asc', range_)
        else:
            c.execute('select * from single_url_queue where id >= ? and id <= ? and archived <> 1 order by id asc', range_)
    return list(c.fetchall())

def get_queued_urls_by_id(url_ids: list[int], archived: bool) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    result = []
    for i in url_ids:
        if archived:
            c.execute('select * from single_url_queue where id = ?', (i,))
        else:
            c.execute('select * from single_url_queue where id = ? and archived <> 1', (i,))
        for row in c.fetchall():
            result.append(row)
    return result

def report(verbose: bool, urls: bool = True, archived: bool = False, paused: bool = False) -> None:
    check_init()
    c = get_conn().cursor()

    def format_date(timestamp: Optional[Union[float, int, str]]) -> str:
        if isinstance(timestamp, str):
            return timestamp
        if timestamp is None:
            return 'never'
        return datetime.datetime.fromtimestamp(float(timestamp)).isoformat()

    archived_condition = "archived = 0"
    if archived:
        archived_condition = "true"

    paused_condition = "paused = 0"
    if paused:
        paused_condition = "true"

    log.info('hydownloader-report', 'Generating report...')
    urls_paused = len(c.execute(f'select * from single_url_queue where {archived_condition} and paused = 1').fetchall())
    subs_paused = len(c.execute('select * from subscriptions where paused = 1').fetchall())
    urls_errored_entries = c.execute(f'select * from single_url_queue where {archived_condition} and status > 0').fetchall()
    urls_errored = len(urls_errored_entries)
    subs_errored_entries = c.execute(f'select * from subscriptions where {paused_condition} and last_check is not null and last_successful_check <> last_check').fetchall()
    subs_errored = len(subs_errored_entries)
    urls_no_files_entries = c.execute(f'select * from single_url_queue where {archived_condition} and status = 0 and (new_files is null or already_seen_files is null or new_files + already_seen_files = 0)').fetchall()
    urls_no_files = len(urls_no_files_entries)
    subs_no_files_entries = c.execute((
        f'select * from subscriptions where {paused_condition} and last_check is not null and id in '
        f'(select subscription_id from subscription_checks group by subscription_id having sum(new_files) + sum(already_seen_files) <= 0)'
    )).fetchall()
    subs_no_files = len(subs_no_files_entries)
    urls_waiting_long_entries = c.execute(f'select * from single_url_queue where {archived_condition} and time_processed is null and time_added + 86400 <= {time.time()}').fetchall()
    urls_waiting_long = len(urls_waiting_long_entries)
    subs_waiting_long_entries = c.execute((
        f'select * from subscriptions where {paused_condition} and (last_check is not null and last_check + check_interval <= {time.time()})'
        f'or (last_check is null and time_created + check_interval <= {time.time()})'
    )).fetchall()
    subs_waiting_long = len(subs_waiting_long_entries)
    subs_no_recent_files_entries = c.execute((
        f'select * from subscriptions where {paused_condition} and last_check is not null and id in '
        f'(select subscription_id from subscription_checks where time_started + 30 * 86400 >= {time.time()} group by subscription_id having sum(new_files) + sum(already_seen_files) <= 0)'
        f'or id in (select subscription_id from subscription_checks group by subscription_id having max(time_started) + 30 * 86400 < {time.time()})'
    )).fetchall()
    subs_no_recent_files = len(subs_no_recent_files_entries)
    subs_queued = len(get_due_subscriptions())
    urls_queued = len(get_urls_to_download())
    all_subs = len(c.execute('select * from subscriptions').fetchall())
    all_urls = len(c.execute(f'select * from single_url_queue where {archived_condition}').fetchall())
    all_sub_checks = len(c.execute(f'select * from subscription_checks').fetchall())
    all_file_results = len(c.execute('select * from additional_data').fetchall())
    last_time_url_processed_results = c.execute(f'select max(time_processed) t from single_url_queue where {archived_condition}').fetchall()
    last_time_url_processed = format_date(last_time_url_processed_results[0]['t'] if last_time_url_processed_results else 'never')
    last_time_sub_checked_results = c.execute(f'select max(time_finished) t from subscription_checks').fetchall()
    last_time_sub_checked = format_date(last_time_sub_checked_results[0]['t'] if last_time_sub_checked_results else 'never')
    time_spent_checking_all = c.execute('select sum(time_finished-time_started) val from subscription_checks').fetchone()['val']
    time_spent_checking_bad = c.execute('select sum(time_finished-time_started) val from subscription_checks where status <> \'ok\'').fetchone()['val']
    time_spent_checking_all_30d = c.execute(f'select sum(time_finished-time_started) val from subscription_checks where time_started > {time.time()}-30*86400').fetchone()['val']
    time_spent_checking_bad_30d = c.execute(f'select sum(time_finished-time_started) val from subscription_checks where status <> \'ok\' and time_started > {time.time()}-30*86400').fetchone()['val']
    time_spent_checking_all_7d = c.execute(f'select sum(time_finished-time_started) val from subscription_checks where time_started > {time.time()}-7*86400').fetchone()['val']
    time_spent_checking_bad_7d = c.execute(f'select sum(time_finished-time_started) val from subscription_checks where status <> \'ok\' and time_started > {time.time()}-7*86400').fetchone()['val']
    calc_median_query = ' select avg(len) val from (select len from checks order by len limit 2 - (select count(*) from checks) % 2 offset (select (count(*) - 1) / 2 from checks))'
    avg_check_time_all = c.execute('select avg(time_finished-time_started) val from subscription_checks').fetchone()['val']
    avg_check_time_good = c.execute('select avg(time_finished-time_started) val from subscription_checks where status = \'ok\'').fetchone()['val']
    avg_check_time_bad = c.execute('select avg(time_finished-time_started) val from subscription_checks where status <> \'ok\'').fetchone()['val']
    median_check_time_all = c.execute('with checks(len) as (select time_finished-time_started from subscription_checks)'+calc_median_query).fetchone()['val']
    median_check_time_good = c.execute('with checks(len) as (select time_finished-time_started from subscription_checks where status = \'ok\')'+calc_median_query).fetchone()['val']
    median_check_time_bad = c.execute('with checks(len) as (select time_finished-time_started from subscription_checks where status <> \'ok\')'+calc_median_query).fetchone()['val']
    avg_check_time_all_30d = c.execute(f'select avg(time_finished-time_started) val from subscription_checks where time_started > {time.time()}-30*86400').fetchone()['val']
    avg_check_time_good_30d = c.execute(f'select avg(time_finished-time_started) val from subscription_checks where status = \'ok\' and time_started > {time.time()}-30*86400').fetchone()['val']
    avg_check_time_bad_30d = c.execute(f'select avg(time_finished-time_started) val from subscription_checks where status <> \'ok\' and time_started > {time.time()}-30*86400').fetchone()['val']
    median_check_time_all_30d = c.execute(f'with checks(len) as (select time_finished-time_started from subscription_checks where time_started > {time.time()}-30*86400)'+calc_median_query).fetchone()['val']
    median_check_time_good_30d = c.execute(f'with checks(len) as (select time_finished-time_started from subscription_checks where status = \'ok\' and time_started > {time.time()}-30*86400)'+calc_median_query).fetchone()['val']
    median_check_time_bad_30d = c.execute(f'with checks(len) as (select time_finished-time_started from subscription_checks where status <> \'ok\' and time_started > {time.time()}-30*86400)'+calc_median_query).fetchone()['val']
    avg_check_time_all_7d = c.execute(f'select avg(time_finished-time_started) val from subscription_checks where time_started > {time.time()}-7*86400').fetchone()['val']
    avg_check_time_good_7d = c.execute(f'select avg(time_finished-time_started) val from subscription_checks where status = \'ok\' and time_started > {time.time()}-7*86400').fetchone()['val']
    avg_check_time_bad_7d = c.execute(f'select avg(time_finished-time_started) val from subscription_checks where status <> \'ok\' and time_started > {time.time()}-7*86400').fetchone()['val']
    median_check_time_all_7d = c.execute(f'with checks(len) as (select time_finished-time_started from subscription_checks where time_started > {time.time()}-7*86400)'+calc_median_query).fetchone()['val']
    median_check_time_good_7d = c.execute(f'with checks(len) as (select time_finished-time_started from subscription_checks where status = \'ok\' and time_started > {time.time()}-7*86400)'+calc_median_query).fetchone()['val']
    median_check_time_bad_7d = c.execute(f'with checks(len) as (select time_finished-time_started from subscription_checks where status <> \'ok\' and time_started > {time.time()}-7*86400)'+calc_median_query).fetchone()['val']
    longest_check = c.execute('select max(time_finished-time_started) val from subscription_checks').fetchone()['val']
    longest_check_30d = c.execute(f'select max(time_finished-time_started) val from subscription_checks where time_started > {time.time()}-30*86400').fetchone()['val']
    longest_check_7d = c.execute(f'select max(time_finished-time_started) val from subscription_checks where time_started > {time.time()}-7*86400').fetchone()['val']

    def seconds_to_str(seconds: int):
        days = seconds // 86400
        seconds = seconds % 86400
        hours = seconds // 3600
        seconds = seconds % 3600
        minutes = seconds // 60
        seconds = seconds % 60
        return f'{days} days {hours} hours {minutes} minutes {seconds} seconds'

    def seconds_to_str_short(seconds: int):
        minutes = seconds // 60
        seconds = seconds % 60
        return f'{minutes} minutes {seconds} seconds'

    def print_url_entries(entries: list[dict]) -> None:
        for url in entries:
            log.info('hydownloader-report', (
                f"URL: {url['url']}, "
                f"status: {url['status_text']} (code: {url['status']}), "
                f"time added: {format_date(url['time_added'])}, "
                f"time processed: {format_date(url['time_processed'])}, "
                f"paused: {url['paused']}"
            ))

    def print_sub_entries(entries: list[dict]) -> None:#keywords,downloader,last_check,last_successful_check, check_interval, paused
        for sub in entries:
            log.info('hydownloader-report', (
                f"Downloader: {sub['downloader']}, "
                f"keywords: {sub['keywords']}, "
                f"last check: {format_date(sub['last_check'])}, "
                f"last successful check: {format_date(sub['last_successful_check'])}, "
                f"check interval: {sub['check_interval']}, "
                f"paused: {sub['paused']}"
            ))

    log.info('hydownloader-report', f'Subscriptions: {all_subs}')
    if urls: log.info('hydownloader-report', f'Single URLs: {all_urls}')
    log.info('hydownloader-report', f'Subscription checks: {all_sub_checks}')
    log.info('hydownloader-report', f'All file results (including duplicates and skipped): {all_file_results}')
    log.info('hydownloader-report', f'Last time a subscription was checked: {last_time_sub_checked}')
    if urls: log.info('hydownloader-report', f'Last time a URL was downloaded: {last_time_url_processed}')
    log.info('hydownloader-report', f'Subscriptions due for a check: {subs_queued}')
    if urls: log.info('hydownloader-report', f'URLs waiting to be downloaded: {urls_queued}')
    log.info('hydownloader-report', f'Paused subscriptions: {subs_paused}')
    if urls: log.info('hydownloader-report', f'Paused URLs: {urls_paused}')
    if urls: log.info('hydownloader-report', f'Errored URLs: {urls_errored}')
    if verbose and urls_errored and urls:
        log.info('hydownloader-report', 'These are the following:')
        print_url_entries(urls_errored_entries)
    log.info('hydownloader-report', f'Errored subscriptions: {subs_errored}')
    if verbose and subs_errored:
        log.info('hydownloader-report', 'These are the following:')
        print_sub_entries(subs_errored_entries)
    if urls: log.info('hydownloader-report', f'URLs that did not error but produced no files: {urls_no_files}')
    if verbose and urls_no_files and urls:
        log.info('hydownloader-report', 'These are the following:')
        print_url_entries(urls_no_files_entries)
    log.info('hydownloader-report', f'Subscriptions that did not error but produced no files: {subs_no_files}')
    if verbose and subs_no_files:
        log.info('hydownloader-report', 'These are the following:')
        print_sub_entries(subs_no_files_entries)
    if urls: log.info('hydownloader-report', f'URLs waiting to be downloaded for more than a day: {urls_waiting_long}')
    if verbose and urls_waiting_long and urls:
        log.info('hydownloader-report', 'These are the following:')
        print_url_entries(urls_waiting_long_entries)
    log.info('hydownloader-report', f'Subscriptions due for a check longer than their check interval: {subs_waiting_long}')
    if verbose and subs_waiting_long:
        log.info('hydownloader-report', 'These are the following:')
        print_sub_entries(subs_waiting_long_entries)
    log.info('hydownloader-report', f'Subscriptions that were checked at least once but did not produce any files in the past 30 days: {subs_no_recent_files}')
    if verbose and subs_no_recent_files:
        log.info('hydownloader-report', 'These are the following:')
        print_sub_entries(subs_no_recent_files_entries)

    log.info('hydownloader-report', 'Time spent checking subs (all time): '+seconds_to_str(int(time_spent_checking_all)))
    log.info('hydownloader-report', 'Time spent checking subs (all time, successful checks): '+seconds_to_str(int(time_spent_checking_all-time_spent_checking_bad)))
    log.info('hydownloader-report', 'Time spent checking subs (all time, failed checks): '+seconds_to_str(int(time_spent_checking_bad)))
    log.info('hydownloader-report', 'Time spent checking subs (past month): '+seconds_to_str(int(time_spent_checking_all_30d)))
    log.info('hydownloader-report', 'Time spent checking subs (past month, successful checks): '+seconds_to_str(int(time_spent_checking_all_30d-time_spent_checking_bad_30d)))
    log.info('hydownloader-report', 'Time spent checking subs (past month, failed checks): '+seconds_to_str(int(time_spent_checking_bad_30d)))
    log.info('hydownloader-report', 'Time spent checking subs (past week): '+seconds_to_str(int(time_spent_checking_all_7d)))
    log.info('hydownloader-report', 'Time spent checking subs (past week, successful checks): '+seconds_to_str(int(time_spent_checking_all_7d-time_spent_checking_bad_7d)))
    log.info('hydownloader-report', 'Time spent checking subs (past week, failed checks): '+seconds_to_str(int(time_spent_checking_bad_7d)))
    log.info('hydownloader-report', 'Average subscription check time (all time): '+seconds_to_str_short(int(avg_check_time_all)))
    log.info('hydownloader-report', 'Average subscription check time (all time, successful checks): '+seconds_to_str_short(int(avg_check_time_good)))
    log.info('hydownloader-report', 'Average subscription check time (all time, failed checks): '+seconds_to_str_short(int(avg_check_time_bad)))
    log.info('hydownloader-report', 'Average subscription check time (past month): '+seconds_to_str_short(int(avg_check_time_all_30d)))
    log.info('hydownloader-report', 'Average subscription check time (past month, successful checks): '+seconds_to_str_short(int(avg_check_time_good_30d)))
    log.info('hydownloader-report', 'Average subscription check time (past month, failed checks): '+seconds_to_str_short(int(avg_check_time_bad_30d)))
    log.info('hydownloader-report', 'Average subscription check time (past week): '+seconds_to_str_short(int(avg_check_time_all_7d)))
    log.info('hydownloader-report', 'Average subscription check time (past week, successful checks): '+seconds_to_str_short(int(avg_check_time_good_7d)))
    log.info('hydownloader-report', 'Average subscription check time (past week, failed checks): '+seconds_to_str_short(int(avg_check_time_bad_7d)))
    log.info('hydownloader-report', 'Median subscription check time (all time): '+seconds_to_str_short(int(median_check_time_all)))
    log.info('hydownloader-report', 'Median subscription check time (all time, successful checks): '+seconds_to_str_short(int(median_check_time_good)))
    log.info('hydownloader-report', 'Median subscription check time (all time, failed checks): '+seconds_to_str_short(int(median_check_time_bad)))
    log.info('hydownloader-report', 'Median subscription check time (past month): '+seconds_to_str_short(int(median_check_time_all_30d)))
    log.info('hydownloader-report', 'Median subscription check time (past month, successful checks): '+seconds_to_str_short(int(median_check_time_good_30d)))
    log.info('hydownloader-report', 'Median subscription check time (past month, failed checks): '+seconds_to_str_short(int(median_check_time_bad_30d)))
    log.info('hydownloader-report', 'Median subscription check time (past week): '+seconds_to_str_short(int(median_check_time_all_7d)))
    log.info('hydownloader-report', 'Median subscription check time (past week, successful checks): '+seconds_to_str_short(int(median_check_time_good_7d)))
    log.info('hydownloader-report', 'Median subscription check time (past week, failed checks): '+seconds_to_str_short(int(median_check_time_bad_7d)))
    log.info('hydownloader-report', 'Longest subscription check (all time): '+seconds_to_str(int(longest_check)))
    log.info('hydownloader-report', 'Longest subscription check (past month): '+seconds_to_str(int(longest_check_30d)))
    log.info('hydownloader-report', 'Longest subscription check (past week): '+seconds_to_str(int(longest_check_7d)))

    log.info('hydownloader-report', 'Report finished')

def add_log_file_to_parse_queue(log_file: str, worker: str) -> None:
    check_init()
    c = get_conn().cursor()
    log_file = os.path.relpath(log_file, start = get_rootpath())
    c.execute('insert into log_files_to_parse(file, worker) values (?, ?)', (log_file,worker))
    get_conn().commit()

def remove_log_file_from_parse_queue(log_file: str) -> None:
    check_init()
    c = get_conn().cursor()
    log_file = os.path.relpath(log_file, start = get_rootpath())
    c.execute('delete from log_files_to_parse where file = ?', (log_file,))
    get_conn().commit()

def get_queued_log_file(worker: Optional[str] = None) -> Optional[str]:
    check_init()
    c = get_conn().cursor()
    if not worker:
        c.execute('select * from log_files_to_parse limit 1')
    else:
        c.execute('select * from log_files_to_parse where worker = ? limit 1', (worker,))
    if obj := c.fetchone():
        return obj['file']
    return None

def add_hydrus_known_url(url: str, status: int) -> None:
    check_init()
    c = get_shared_conn().cursor()
    c.execute('insert into known_urls(url,status) values (?,?)', (url, status))

def delete_all_hydrus_known_urls() -> None:
    check_init()
    c = get_shared_conn().cursor()
    c.execute('delete from known_urls where status <> 0')

def close_thread_connections() -> None:
    global _closed_threads, _inited
    if not _inited: return
    thread_id = threading.get_ident()
    with _closed_threads_lock:
        if thread_id in _closed_threads:
            return
    get_conn().commit()
    get_shared_conn().commit()
    get_conn().close()
    get_shared_conn().close()
    with _closed_threads_lock:
        _closed_threads.add(threading.get_ident())

def shutdown() -> None:
    global _inited
    if not _inited: return
    close_thread_connections()
    _inited = False

def add_known_urls(urls: list[str], subscription_id: Optional[int] = None, url_id: Optional[int] = None) -> None:
    check_init()
    c = get_conn().cursor()
    s_c = get_shared_conn().cursor()
    for url in urls:
        c.execute('select * from known_urls where url = ? and subscription_id is ? and url_id is ? limit 1', (url, subscription_id, url_id))
        if not c.fetchone():
            c.execute('insert into known_urls(url,subscription_id,url_id,status,time_added) values (?,?,?,?,?)', (url,subscription_id,url_id,0,time.time()))
        s_c.execute('select * from known_urls where url = ? and status = 0', (url,))
        if not s_c.fetchone():
            s_c.execute('insert into known_urls(url,status) values (?,0)',(url,))
    get_conn().commit()
    get_shared_conn().commit()

def get_known_urls(patterns: set[str]) -> list[dict]:
    check_init()
    c = get_shared_conn().cursor()
    # where = " or ".join({("url like ?" if "%" in pattern else "url = ?") for pattern in patterns})
    where = "url in (" + ",".join(["?"]*len(patterns)) + ")"
    c.execute("select * from known_urls where "+where, tuple(patterns))
    return c.fetchall()

def get_conf(name : str, optional: bool = False, no_check: bool = False) -> Optional[Union[str, int, bool, dict]]:
    if not no_check: check_init()
    if name in _config:
        return _config[name]
    if name in C.DEFAULT_CONFIG:
        log.warning("hydownloader", f'Configuration key not found in user config, default value was used: {name}')
        return C.DEFAULT_CONFIG[name]
    if not optional:
        log.fatal("hydownloader", f'Invalid configuration key: {name}')
    else:
        return None

def check_import_db(path: str) -> tuple[bool, Optional[float], Optional[float]]:
    check_init()
    c = get_shared_conn().cursor()
    c.execute("select * from imported_files where filename = ? limit 1",(path,))
    if row := c.fetchone():
        return True, row['modification_time'], row['creation_time']
    return False, None, None

def add_or_update_import_entry(path: str, import_time: float, creation_time: float, modification_time: float, metadata: Optional[bytes], hexdigest: str) -> None:
    check_init()
    c = get_shared_conn().cursor()
    c.execute("select * from imported_files where filename = ? limit 1",(path,))
    if c.fetchone():
        c.execute("update imported_files set import_time = ?, creation_time = ?, modification_time = ?, metadata = ?, hash = ? where filename = ?", (import_time, creation_time, modification_time, metadata, hexdigest, path))
    else:
        c.execute("insert into imported_files(filename,import_time,creation_time,modification_time,metadata,hash) values (?,?,?,?,?,?)", (path,import_time,creation_time,modification_time,metadata,hexdigest))

def get_unprocessed_reverse_lookup_jobs() -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.execute('select * from reverse_lookup_jobs where status = -1 and paused <> 1 order by priority desc, time_added desc')
    return c.fetchall()

def add_or_update_reverse_lookup_jobs(jobs: list[dict]) -> bool:
    check_init()
    for item in jobs:
        add = "id" not in item
        if add and not "file_url" in item and not "file_path" in item: continue
        if add: item["time_added"] = time.time()
        if 'file_url' in item: item['file_url'] = uri_normalizer.normalizes(item['file_url'])
        if add:
            defaults = get_conf('reverse-lookup-defaults', True)
            if defaults:
                for key in defaults:
                    if not key in item: item[key] = defaults[key]
        upsert_dict("reverse_lookup_jobs", item, no_commit = True)
        if add:
            log.info("hydownloader", f"Added reverse lookup job with file {item['file_path']} and URL {item['file_url']}")
        else:
            log.info("hydownloader", f"Updated reverse lookup job with ID {item['id']}")
    get_conn().commit()
    return True

def delete_reverse_lookup_jobs(job_ids: list[int]) -> bool:
    check_init()
    c = get_conn().cursor()
    for i in job_ids:
        c.execute('delete from reverse_lookup_jobs where id = ?', (i,))
    get_conn().commit()
    log.info("hydownloader", f"Deleted reverse lookup jobs with IDs: {', '.join(map(str, job_ids))}")
    return True

def get_reverse_lookup_jobs_by_range(archived: bool, range_: Optional[tuple[int, int]] = None) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    c.arraysize = 1000
    if range_ is None:
        if archived:
            c.execute('select * from reverse_lookup_jobs order by id asc')
        else:
            c.execute('select * from reverse_lookup_jobs where archived <> 1 order by id asc')
    else:
        if archived:
            c.execute('select * from reverse_lookup_jobs where id >= ? and id <= ? order by id asc', range_)
        else:
            c.execute('select * from reverse_lookup_jobs where id >= ? and id <= ? and archived <> 1 order by id asc', range_)
    return list(c.fetchall())

def get_reverse_lookup_jobs_by_id(job_ids: list[int], archived: bool) -> list[dict]:
    check_init()
    c = get_conn().cursor()
    result = []
    for i in job_ids:
        if archived:
            c.execute('select * from reverse_lookup_jobs where id = ?', (i,))
        else:
            c.execute('select * from reverse_lookup_jobs where id = ? and archived <> 1', (i,))
        for row in c.fetchall():
            result.append(row)
    return result
