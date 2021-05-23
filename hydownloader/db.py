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

import sqlite3
import os
import os.path
import json
import time
import urllib.parse
import datetime
from typing import Optional, Union
from hydownloader import log, uri_normalizer, __version__, constants as C

_conn: sqlite3.Connection = None # type: ignore
_shared_conn: sqlite3.Connection = None # type: ignore
_path: str = None # type: ignore
_config: dict = None # type: ignore
_inited = False

def upsert_dict(table: str, d: dict, no_commit: bool = False) -> None:
    keys = d.keys()
    column_names = ",".join(keys)
    placeholders = ",".join(["?"]*len(keys))
    update_part = ",".join(f"{key}=?" for key in keys if key not in ("id", "rowid"))
    values = []
    c = _conn.cursor()
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
    if not no_commit: _conn.commit()

def init(path : str) -> None:
    global _conn, _shared_conn, _inited, _path, _config
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
        gdl_cfg = open(path+"/gallery-dl-config.json", 'w', encoding='utf-8-sig')
        gdl_cfg.write(C.DEFAULT_GALLERY_DL_CONFIG)
        gdl_cfg.close()
    if not os.path.isfile(path+"/gallery-dl-user-config.json"):
        gdl_cfg = open(path+"/gallery-dl-user-config.json", 'w', encoding='utf-8-sig')
        gdl_cfg.write(C.DEFAULT_GALLERY_DL_USER_CONFIG)
        gdl_cfg.close()
    if not os.path.isfile(path+"/hydownloader-config.json"):
        hydl_cfg = open(path+"/hydownloader-config.json", 'w', encoding='utf-8-sig')
        hydl_cfg.write(json.dumps(C.DEFAULT_CONFIG, indent=4))
        hydl_cfg.close()
    if not os.path.isfile(path+"/cookies.txt"):
        open(path+"/cookies.txt", "w", encoding="utf-8-sig").close()
    _conn = sqlite3.connect(path+"/hydownloader.db", check_same_thread=False, timeout=24*60*60)
    _conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    if needs_db_init: create_db()
    _config = json.load(open(path+"/hydownloader-config.json", "r", encoding="utf-8-sig"))

    shared_db_path = path+"/hydownloader.shared.db"
    if _config["shared-db-override"]:
        shared_db_path = _config["shared-db-override"]
    need_shared_db_init = not os.path.isfile(shared_db_path)
    _shared_conn = sqlite3.connect(shared_db_path, check_same_thread=False, timeout=24*60*60)
    _shared_conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    if need_shared_db_init: create_shared_db()

    check_db_version()

    _inited = True

def create_db() -> None:
    c = _conn.cursor()
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
    c.execute('insert into version(version) values (?)', (__version__,))
    _conn.commit()

def create_shared_db() -> None:
    c = _shared_conn.cursor()
    c.execute(C.SHARED_CREATE_KNOWN_URLS_STATEMENT)
    c.execute(C.SHARED_CREATE_KNOWN_URL_INDEX_STATEMENT)
    _shared_conn.commit()

def get_rootpath() -> str:
    check_init()
    return _path

def associate_additional_data(filename: str, subscription_id: Optional[int] = None, url_id: Optional[int] = None, no_commit: bool = False) -> None:
    check_init()
    if subscription_id is None and url_id is None: raise ValueError("associate_additional_data: both IDs cannot be None")
    filename = os.path.relpath(filename, get_rootpath())
    c = _conn.cursor()
    data = None
    already_saved = 0
    if subscription_id is not None:
        c.execute('select additional_data from subscriptions where id = ?', (subscription_id,))
        rows = c.fetchall()
        if len(rows): data = rows[0]['additional_data']
        c.execute('select * from additional_data where file = ? and subscription_id = ? and data = ?', (filename, subscription_id, data))
        already_saved = len(c.fetchall())
    else:
        c.execute('select additional_data from single_url_queue where id = ?', (url_id,))
        rows = c.fetchall()
        if len(rows): data = rows[0]['additional_data']
        c.execute('select * from additional_data where file = ? and url_id = ? and data = ?', (filename, url_id, data))
        already_saved = len(c.fetchall())
    if already_saved == 0:
        c.execute('insert into additional_data(file, data, subscription_id, url_id, time_added) values (?,?,?,?,?)', (filename, data, subscription_id, url_id, time.time()))
    if not no_commit: _conn.commit()

def get_last_files_for_url(url_id: int) -> list[str]:
    check_init()
    result = []
    c = _conn.cursor()
    c.execute('select file from additional_data where url_id = ? order by time_added desc limit 5', (url_id,))
    for item in c.fetchall():
        result.append(get_rootpath()+"/"+item['file'])
    return result

def get_last_files_for_sub(sub_id: int) -> list[str]:
    check_init()
    result = []
    c = _conn.cursor()
    c.execute('select file from additional_data where subscription_id = ? order by time_added desc limit 5', (sub_id,))
    for item in c.fetchall():
        result.append(get_rootpath()+"/"+item['file'])
    return result

def sync() -> None:
    check_init()
    _conn.commit()
    _shared_conn.commit()

def check_init() -> None:
    if not _inited:
        log.fatal("hydownloader", "Database used but not initalized")

def check_db_version() -> None:
    c = _conn.cursor()
    c.execute('select version from version')
    v = c.fetchall()
    if len(v) != 1:
        log.fatal("hydownloader", "Invalid version table in hydownloader database")
    if v[0]['version'] != __version__:
        log.fatal("hydownloader", "Unsupported hydownloader database version found")

def get_due_subscriptions() -> list[dict]:
    check_init()
    c = _conn.cursor()
    c.execute(f'select * from subscriptions where paused <> 1 and (last_successful_check + check_interval <= {time.time()} or last_successful_check is null) order by priority desc')
    return c.fetchall()

def get_urls_to_download() -> list[dict]:
    check_init()
    c = _conn.cursor()
    c.execute('select * from single_url_queue where status = -1 and paused <> 1 order by priority desc, time_added desc')
    return c.fetchall()

def add_or_update_urls(url_data: list[dict]) -> bool:
    check_init()
    for item in url_data:
        add = "id" not in item
        if add and not "url" in item: continue
        if add: item["time_added"] = time.time()
        if 'url' in item: item['url'] = uri_normalizer.normalizes(item['url'])
        upsert_dict("single_url_queue", item, no_commit = True)
        if add:
            log.info("hydownloader", f"Added URL: {item['url']}")
        else:
            log.info("hydownloader", f"Updated URL with ID {item['id']}")
    _conn.commit()
    return True

def check_single_queue_for_url(url: str) -> list[dict]:
    check_init()
    c = _conn.cursor()
    url = uri_normalizer.normalizes(url)
    c.execute('select * from single_url_queue where url = ?', (url,))
    return c.fetchall()

def get_subscriptions_by_downloader_data(downloader: str, keywords: str) -> list[dict]:
    check_init()
    c = _conn.cursor()
    c.execute("select * from subscriptions where downloader = ? and keywords = ?", (downloader, keywords))
    results = c.fetchall()
    if not results: # if nothing found, try the unquoted version too
        c.execute("select * from subscriptions where downloader = ? and keywords = ?", (downloader, urllib.parse.unquote(keywords)))
        results = c.fetchall()
    return results

def add_or_update_subscriptions(sub_data: list[dict]) -> bool:
    check_init()
    for item in sub_data:
        add = "id" not in item
        if add and not "keywords" in item: continue
        if add and not "downloader" in item: continue
        if add and not "additional_data" in item: item["additional_data"] = ""
        if add: item["time_created"] = time.time()
        upsert_dict("subscriptions", item, no_commit = True)
        if add:
            log.info("hydownloader", f"Added subscription: {item['keywords']} for downloader {item['downloader']}")
        else:
            log.info("hydownloader", f"Updated subscription with ID {item['id']}")
    _conn.commit()
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
    _conn.commit()
    return True

def add_subscription_check(subscription_id: int, new_files: int, already_seen_files: int, time_started: Union[float,int], time_finished: Union[float,int], status: str) -> None:
    check_init()
    c = _conn.cursor()
    c.execute('insert into subscription_checks(subscription_id, new_files, already_seen_files, time_started, time_finished, status) values (?,?,?,?,?,?)', (subscription_id,new_files,already_seen_files,time_started,time_finished,status))
    _conn.commit()

def get_subscription_checks(subscription_id: Optional[int], archived: bool) -> list[dict]:
    check_init()
    c = _conn.cursor()
    if subscription_id:
        if archived:
            c.execute('select rowid, * from subscription_checks where subscription_id = ? order by rowid asc', (subscription_id,))
        else:
            c.execute('select rowid, * from subscription_checks where subscription_id = ? and archived <> 1 order by rowid asc', (subscription_id,))
    else:
        if archived:
            c.execute('select rowid, * from subscription_checks order by rowid asc')
        else:
            c.execute('select rowid, * from subscription_checks where archived <> 1 order by rowid asc')
    return list(c.fetchall())

def delete_urls(url_ids: list[int]) -> bool:
    check_init()
    c = _conn.cursor()
    for i in url_ids:
        c.execute('delete from single_url_queue where id = ?', (i,))
    _conn.commit()
    log.info("hydownloader", f"Deleted URLs with IDs: {', '.join(map(str, url_ids))}")
    return True

def delete_subscriptions(sub_ids: list[int]) -> bool:
    check_init()
    c = _conn.cursor()
    for i in sub_ids:
        c.execute('delete from subscriptions where id = ?', (i,))
    _conn.commit()
    log.info("hydownloader", f"Deleted subscriptions with IDs: {', '.join(map(str, sub_ids))}")
    return True

def get_subs_by_range(range_: Optional[tuple[int, int]] = None) -> list[dict]:
    check_init()
    c = _conn.cursor()
    if range_ is None:
        c.execute('select * from subscriptions order by id asc')
    else:
        c.execute('select * from subscriptions where id >= ? and id <= ? order by id asc', range_)
    return list(c.fetchall())

def get_subs_by_id(sub_ids: list[int]) -> list[dict]:
    check_init()
    c = _conn.cursor()
    result = []
    for i in sub_ids:
        c.execute('select * from subscriptions where id = ?', (i,))
        for row in c.fetchall():
            result.append(row)
    return result

def get_queued_urls_by_range(archived: bool, range_: Optional[tuple[int, int]] = None) -> list[dict]:
    check_init()
    c = _conn.cursor()
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
    c = _conn.cursor()
    result = []
    for i in url_ids:
        if archived:
            c.execute('select * from single_url_queue where id = ?', (i,))
        else:
            c.execute('select * from single_url_queue where id = ? and archived <> 1', (i,))
        for row in c.fetchall():
            result.append(row)
    return result

def report(verbose: bool) -> None:
    check_init()
    c = _conn.cursor()

    def format_date(timestamp: Optional[Union[float, int, str]]) -> str:
        if isinstance(timestamp, str):
            return timestamp
        if timestamp is None:
            return 'never'
        return datetime.datetime.fromtimestamp(float(timestamp)).isoformat()

    log.info('hydownloader-report', 'Generating report...')
    urls_paused = len(c.execute('select * from single_url_queue where paused = 1').fetchall())
    subs_paused = len(c.execute('select * from subscriptions where paused = 1').fetchall())
    urls_errored_entries = c.execute('select * from single_url_queue where status > 0').fetchall()
    urls_errored = len(urls_errored_entries)
    subs_errored_entries = c.execute('select * from subscriptions where last_check is not null and last_successful_check <> last_check').fetchall()
    subs_errored = len(subs_errored_entries)
    urls_no_files_entries = c.execute('select * from single_url_queue where status = 0 and (new_files is null or already_seen_files is null or new_files + already_seen_files = 0)').fetchall()
    urls_no_files = len(urls_no_files_entries)
    subs_no_files_entries = c.execute((
        'select * from subscriptions where last_check is not null and id in '
        '(select subscription_id from subscription_checks group by subscription_id having sum(new_files) + sum(already_seen_files) <= 0)'
    )).fetchall()
    subs_no_files = len(subs_no_files_entries)
    urls_waiting_long_entries = c.execute(f'select * from single_url_queue where time_processed is null and time_added + 86400 <= {time.time()}').fetchall()
    urls_waiting_long = len(urls_waiting_long_entries)
    subs_waiting_long_entries = c.execute((
        f'select * from subscriptions where (last_check is not null and last_check + check_interval <= {time.time()})'
        f'or (last_check is null and time_created + check_interval <= {time.time()})'
    )).fetchall()
    subs_waiting_long = len(subs_waiting_long_entries)
    subs_no_recent_files_entries = c.execute((
        'select * from subscriptions where last_check is not null and id in '
        f'(select subscription_id from subscription_checks where time_started + 30 * 86400 >= {time.time()} group by subscription_id having sum(new_files) + sum(already_seen_files) <= 0)'
        f'or id not in (select subscription_id from subscription_checks group by subscription_id having max(time_started) + 30 * 86400 < {time.time()})'
    )).fetchall()
    subs_no_recent_files = len(subs_no_recent_files_entries)
    subs_queued = len(get_due_subscriptions())
    urls_queued = len(get_urls_to_download())
    all_subs = len(c.execute('select * from subscriptions').fetchall())
    all_urls = len(c.execute('select * from single_url_queue').fetchall())
    all_sub_checks = len(c.execute('select * from subscription_checks').fetchall())
    all_file_results = len(c.execute('select * from additional_data').fetchall())
    last_time_url_processed_results = c.execute('select max(time_processed) t from single_url_queue').fetchall()
    last_time_url_processed = format_date(last_time_url_processed_results[0]['t'] if last_time_url_processed_results else 'never')
    last_time_sub_checked_results = c.execute('select max(time_finished) t from subscription_checks').fetchall()
    last_time_sub_checked = format_date(last_time_sub_checked_results[0]['t'] if last_time_sub_checked_results else 'never')

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
    log.info('hydownloader-report', f'Single URLs: {all_urls}')
    log.info('hydownloader-report', f'Subscription checks: {all_sub_checks}')
    log.info('hydownloader-report', f'All file results (including duplicates and skipped): {all_file_results}')
    log.info('hydownloader-report', f'Last time a subscription was checked: {last_time_sub_checked}')
    log.info('hydownloader-report', f'Last time a URL was downloaded: {last_time_url_processed}')
    log.info('hydownloader-report', f'Subscriptions due for a check: {subs_queued}')
    log.info('hydownloader-report', f'URLs waiting to be downloaded: {urls_queued}')
    log.info('hydownloader-report', f'Paused subscriptions: {subs_paused}')
    log.info('hydownloader-report', f'Paused URLs: {urls_paused}')
    log.info('hydownloader-report', f'Errored URLs: {urls_errored}')
    if verbose and urls_errored:
        log.info('hydownloader-report', 'These are the following:')
        print_url_entries(urls_errored_entries)
    log.info('hydownloader-report', f'Errored subscriptions: {subs_errored}')
    if verbose and subs_errored:
        log.info('hydownloader-report', 'These are the following:')
        print_sub_entries(subs_errored_entries)
    log.info('hydownloader-report', f'URLs that did not error but produced no files: {urls_no_files}')
    if verbose and urls_no_files:
        log.info('hydownloader-report', 'These are the following:')
        print_url_entries(urls_no_files_entries)
    log.info('hydownloader-report', f'Subscriptions that did not error but produced no files: {subs_no_files}')
    if verbose and subs_no_files:
        log.info('hydownloader-report', 'These are the following:')
        print_sub_entries(subs_no_files_entries)
    log.info('hydownloader-report', f'URLs waiting to be downloaded for more than a day: {urls_waiting_long}')
    if verbose and urls_waiting_long:
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

    log.info('hydownloader-report', 'Report finished')

def add_log_file_to_parse_queue(log_file: str) -> None:
    check_init()
    c = _conn.cursor()
    log_file = os.path.relpath(log_file, start = get_rootpath())
    c.execute('insert into log_files_to_parse(file) values (?)', (log_file,))
    _conn.commit()

def remove_log_file_from_parse_queue(log_file: str) -> None:
    check_init()
    c = _conn.cursor()
    log_file = os.path.relpath(log_file, start = get_rootpath())
    c.execute('delete from log_files_to_parse where file = ?', (log_file,))
    _conn.commit()

def get_queued_log_file() -> Optional[str]:
    check_init()
    c = _conn.cursor()
    c.execute('select * from log_files_to_parse limit 1')
    if obj := c.fetchone():
        return obj['file']
    return None

def add_hydrus_known_url(url: str, status: int) -> None:
    check_init()
    c = _shared_conn.cursor()
    c.execute('insert into known_urls(url,status) values (?,?)', (url, status))

def delete_all_hydrus_known_urls() -> None:
    check_init()
    c = _shared_conn.cursor()
    c.execute('delete from known_urls where status <> 0')

def shutdown() -> None:
    global _inited
    if not _inited: return
    _conn.commit()
    _shared_conn.commit()
    _inited = False
    _conn.close()
    _shared_conn.close()

def add_known_urls(urls: list[str], subscription_id: Optional[int] = None, url_id: Optional[int] = None) -> None:
    check_init()
    c = _conn.cursor()
    s_c = _shared_conn.cursor()
    for url in urls:
        c.execute('select * from known_urls where url = ? and subscription_id is ? and url_id is ? limit 1', (url, subscription_id, url_id))
        if not c.fetchone():
            c.execute('insert into known_urls(url,subscription_id,url_id,status,time_added) values (?,?,?,?,?)', (url,subscription_id,url_id,0,time.time()))
        s_c.execute('select * from known_urls where url = ? and status = 0', (url,))
        if not s_c.fetchone():
            s_c.execute('insert into known_urls(url,status) values (?,0)',(url,))
    _conn.commit()
    _shared_conn.commit()

def get_known_urls(patterns: set[str]) -> list[dict]:
    check_init()
    c = _shared_conn.cursor()
    # where = " or ".join({("url like ?" if "%" in pattern else "url = ?") for pattern in patterns})
    where = "url in (" + ",".join(["?"]*len(patterns)) + ")"
    c.execute("select * from known_urls where "+where, tuple(patterns))
    return c.fetchall()

def get_conf(name : str) -> Union[str, int, bool]:
    check_init()
    if name in _config:
        return _config[name]
    if name in C.DEFAULT_CONFIG:
        log.warning("hydownloader", f'Configuration key not found in user config, default value was used: {name}')
        return C.DEFAULT_CONFIG[name]
    log.fatal("hydownloader", f'Invalid configuration key: {name}')
