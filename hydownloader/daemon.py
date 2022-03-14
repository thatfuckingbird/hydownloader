#!/usr/bin/env python3

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

import sys
import os
import threading
import time
import json
import atexit
import signal
import http.cookiejar as ck
from wsgiref.simple_server import make_server, WSGIRequestHandler
import ssl
import click
import bottle
from bottle import route, hook
from hydownloader import db, log, gallery_dl_utils, urls, __version__, tools, constants, output_postprocessors

class SSLWSGIRefServer(bottle.ServerAdapter):
    def __init__(self, ssl_cert : str, **kwargs):
        super().__init__(**kwargs)
        self.ssl_cert = ssl_cert
        self.srv = None

    def run(self, handler):
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(self, *args, **kw): pass
            self.options['handler_class'] = QuietHandler
        self.srv = make_server(self.host, self.port, handler, **self.options)
        if self.ssl_cert:
            context = ssl.create_default_context()
            context.load_cert_chain(certfile=self.ssl_cert)
            self.srv.socket = context.wrap_socket(self.srv.socket, server_side=True)
        self.srv.serve_forever()

    def stop(self):
        if self.srv: self.srv.shutdown()

_worker_lock = threading.Lock()
_status_lock = threading.Lock()
_end_threads_flag = False
_sub_worker_ended_flag = True
_url_worker_ended_flag = True
_reverse_lookup_worker_ended_flag = True
_sub_worker_paused_flag = False
_url_worker_paused_flag = False
_reverse_lookup_worker_paused_flag = False
_shutdown_started = False
_shutdown_requested_by_api_thread = False
_url_worker_last_status = "no information"
_sub_worker_last_status = "no information"
_reverse_lookup_worker_last_status = "no information"
_url_worker_last_update_time : float = 0
_sub_worker_last_update_time : float = 0
_reverse_lookup_worker_last_update_time : float = 0
_srv = None

def capitalize_first_char(text: str) -> str:
    if text:
        return text[0].upper() + text[1:]
    return ""

def set_url_worker_status(text: str) -> None:
    global _url_worker_last_status, _url_worker_last_update_time
    with _status_lock:
        _url_worker_last_status = text
        _url_worker_last_update_time = time.time()

def set_subscription_worker_status(text: str) -> None:
    global _sub_worker_last_status, _sub_worker_last_update_time
    with _status_lock:
        _sub_worker_last_status = text
        _sub_worker_last_update_time = time.time()

def set_reverse_lookup_worker_status(text: str) -> None:
    global _reverse_lookup_worker_last_status, _reverse_lookup_worker_last_update_time
    with _status_lock:
        _reverse_lookup_worker_last_status = text
        _reverse_lookup_worker_last_update_time = time.time()

def end_downloader_threads() -> None:
    global _end_threads_flag
    with _worker_lock:
        _end_threads_flag = True
    while not (_sub_worker_ended_flag and _url_worker_ended_flag and _reverse_lookup_worker_ended_flag):
        time.sleep(1)

def subscription_worker() -> None:
    global _sub_worker_ended_flag
    proc_id = 'sub worker'
    try:
        log.info("hydownloader", "Starting subscription worker thread...")
        with _worker_lock:
            _sub_worker_ended_flag = False
        while True:
            time.sleep(2)
            with _worker_lock:
                if _end_threads_flag:
                    break
            subs_due = db.get_due_subscriptions()
            if not subs_due:
                with _worker_lock:
                    if _sub_worker_paused_flag:
                        set_subscription_worker_status("paused")
                    else:
                        set_subscription_worker_status("nothing to do: checked for due subscriptions, found none")
            sub = subs_due[0] if subs_due else None
            while sub:
                with _worker_lock:
                    if _end_threads_flag:
                        break
                    if _sub_worker_paused_flag:
                        set_subscription_worker_status("paused")
                        break
                initial_check = sub['last_check'] is None
                url = urls.subscription_data_to_url(sub['downloader'], sub['keywords'])
                check_started_time = time.time()
                status_msg = f"checking subscription: {sub['id']} (downloader: {sub['downloader']}, keywords: {sub['keywords']})"
                set_subscription_worker_status(status_msg)
                missed_sub_check_rowid = db.add_missed_subscription_check(sub['id'], 0, None)
                if sub['last_check'] and sub['last_check'] + 2*sub['check_interval'] <= time.time():
                    db.add_missed_subscription_check(sub['id'], 1, str(time.time()-sub['last_check']))
                log.info(f"subscription-{sub['id']}", capitalize_first_char(status_msg))
                if initial_check:
                    log.info(f"subscription-{sub['id']}", "This is the first check for this subscription")
                result = gallery_dl_utils.run_gallery_dl(
                    url=url,
                    ignore_anchor=False,
                    metadata_only=False,
                    log_file=db.get_rootpath()+f"/logs/subscription-{sub['id']}-gallery-dl-latest.txt",
                    old_log_file=db.get_rootpath()+f"/logs/subscription-{sub['id']}-gallery-dl-old.txt",
                    console_output_file=db.get_rootpath()+f"/temp/subscription-{sub['id']}-gallery-dl-output.txt",
                    unsupported_urls_file=db.get_rootpath()+f"/logs/subscription-{sub['id']}-unsupported-urls-gallery-dl-latest.txt",
                    old_unsupported_urls_file=db.get_rootpath()+f"/logs/subscription-{sub['id']}-unsupported-urls-gallery-dl-old.txt",
                    overwrite_existing=False,
                    filter_=sub['filter'],
                    chapter_filter=None,
                    subscription_mode=True,
                    abort_after=sub['abort_after'],
                    max_file_count = sub['max_files_initial'] if initial_check else sub['max_files_regular'],
                    process_id = proc_id,
                    gallerydl_config = sub['gallerydl_config'],
                    url_metadata_key_name = f"gallerydl_file_url_sub_{sub['id']}"
                    )
                new_sub_data = {
                    'id': sub['id']
                }
                if result:
                    log.warning(f"subscription-{sub['id']}", "Error: "+result)
                else:
                    new_sub_data['last_successful_check'] = check_started_time
                new_sub_data['last_check'] = check_started_time
                new_files, skipped_files = output_postprocessors.process_additional_data(subscription_id = sub['id'])
                output_postprocessors.parse_log_files(False, proc_id)
                check_ended_time = time.time()
                db.add_subscription_check(sub['id'], new_files=new_files, already_seen_files=skipped_files, time_started=check_started_time, time_finished=check_ended_time, status=result if result else 'ok')
                if result and new_files > 0:
                    db.add_missed_subscription_check(sub['id'], 2, result)
                db.add_or_update_subscriptions([new_sub_data])
                db.delete_missed_subscription_check(missed_sub_check_rowid)
                status_msg = f"finished checking subscription: {sub['id']} (downloader: {sub['downloader']}, keywords: {sub['keywords']}), new files: {new_files}, skipped: {skipped_files}"
                set_subscription_worker_status(status_msg)
                log.info(f"subscription-{sub['id']}", capitalize_first_char(status_msg))
                subs_due = db.get_due_subscriptions()
                sub = subs_due[0] if subs_due else None
            with _worker_lock:
                if _end_threads_flag:
                    break
        with _worker_lock:
            if _end_threads_flag:
                log.info("hydownloader", "Stopping subscription worker thread")
                _sub_worker_ended_flag = True
                db.close_thread_connections()
        set_subscription_worker_status('shut down')
    except Exception as e:
        log.error("hydownloader", "Uncaught exception in subscription worker thread", e)
        with _worker_lock:
            _sub_worker_ended_flag = True
        db.close_thread_connections()
        shutdown()

def url_queue_worker() -> None:
    global _url_worker_ended_flag
    proc_id = 'url worker'
    try:
        log.info("hydownloader", "Starting single URL queue worker thread...")
        with _worker_lock:
            _url_worker_ended_flag = False
        while True:
            time.sleep(2)
            with _worker_lock:
                if _end_threads_flag:
                    break
            urls_to_dl = db.get_urls_to_download()
            if not urls_to_dl:
                with _worker_lock:
                    if _url_worker_paused_flag:
                        set_url_worker_status("paused")
                    else:
                        set_url_worker_status("nothing to do: checked for queued URLs, found none")
            urlinfo = urls_to_dl[0] if urls_to_dl else None
            while urlinfo:
                with _worker_lock:
                    if _end_threads_flag:
                        break
                    if _url_worker_paused_flag:
                        set_url_worker_status("paused")
                        break
                check_time = time.time()
                status_msg = f"downloading URL: {urlinfo['url']}"
                set_url_worker_status(status_msg)
                log.info("single url downloader", capitalize_first_char(status_msg))
                result = gallery_dl_utils.run_gallery_dl(
                    url=urlinfo['url'],
                    ignore_anchor=urlinfo['ignore_anchor'],
                    metadata_only=urlinfo['metadata_only'],
                    log_file=db.get_rootpath()+f"/logs/single-urls-{urlinfo['id']}-gallery-dl-latest.txt",
                    old_log_file=db.get_rootpath()+f"/logs/single-urls-{urlinfo['id']}-gallery-dl-old.txt",
                    console_output_file=db.get_rootpath()+f"/temp/single-url-{urlinfo['id']}-gallery-dl-output.txt",
                    unsupported_urls_file=db.get_rootpath()+f"/logs/single-urls-{urlinfo['id']}-unsupported-urls-gallery-dl-latest.txt",
                    old_unsupported_urls_file=db.get_rootpath()+f"/logs/single-urls-{urlinfo['id']}-unsupported-urls-gallery-dl-old.txt",
                    overwrite_existing=urlinfo['overwrite_existing'],
                    filter_=urlinfo['filter'],
                    chapter_filter=None,
                    subscription_mode=False,
                    max_file_count = urlinfo['max_files'],
                    process_id = proc_id,
                    gallerydl_config = urlinfo['gallerydl_config'],
                    url_metadata_key_name = f"gallerydl_file_url_singleurl_{urlinfo['id']}"
                    )
                new_url_data = {
                    'id': urlinfo['id']
                }
                if result:
                    log.warning("single url downloader", f"Error while downloading {urlinfo['url']}: {result}")
                    new_url_data['status'] = 1
                    new_url_data['status_text'] = result
                else:
                    new_url_data['status'] = 0
                    new_url_data['status_text'] = 'ok'
                new_url_data['time_processed'] = check_time
                new_files, skipped_files = output_postprocessors.process_additional_data(url_id = urlinfo['id'])
                output_postprocessors.parse_log_files(False, proc_id)
                new_url_data['new_files'] = new_files
                new_url_data['already_seen_files'] = skipped_files
                db.add_or_update_urls([new_url_data])
                status_msg = f"finished checking URL: {urlinfo['url']}, new files: {new_files}, skipped: {skipped_files}"
                set_url_worker_status(status_msg)
                log.info("single url downloader", capitalize_first_char(status_msg))
                urls_to_dl = db.get_urls_to_download()
                urlinfo = urls_to_dl[0] if urls_to_dl else None
            with _worker_lock:
                if _end_threads_flag:
                    break
        with _worker_lock:
            if _end_threads_flag:
                log.info("hydownloader", "Stopping single URL queue worker thread")
                _url_worker_ended_flag = True
                db.close_thread_connections()
        set_url_worker_status('shut down')
    except Exception as e:
        log.error("hydownloader", "Uncaught exception in URL worker thread", e)
        with _worker_lock:
            _url_worker_ended_flag = True
        db.close_thread_connections()
        shutdown()

def reverse_lookup_worker() -> None:
    global _reverse_lookup_worker_ended_flag
    proc_id = 'rev worker'
    try:
        log.info("hydownloader", "Starting reverse lookup worker thread...")
        with _worker_lock:
            _reverse_lookup_worker_ended_flag = False
        while True:
            time.sleep(2)
            with _worker_lock:
                if _end_threads_flag:
                    break
            #TODO: get outstanding work here
            if True:#if no work to do
                with _worker_lock:
                    if _reverse_lookup_worker_paused_flag:
                        set_reverse_lookup_worker_status("paused")
                    else:
                        set_reverse_lookup_worker_status("nothing to do: checked for reverse lookup jobs, found none")
            while False: #TODO while there are jobs to do
                with _worker_lock:
                    if _end_threads_flag:
                        break
                    if _reverse_lookup_worker_paused_flag:
                        set_reverse_lookup_worker_status("paused")
                        break
                check_time = time.time()
                #status_msg = f"downloading URL: {urlinfo['url']}"
                #set_url_worker_status(status_msg)
                #log.info("single url downloader", capitalize_first_char(status_msg))
                #TODO: do work here
                #status_msg = f"finished checking URL: {urlinfo['url']}, new files: {new_files}, skipped: {skipped_files}"
                #set_url_worker_status(status_msg)
                #log.info("single url downloader", capitalize_first_char(status_msg))
                #urls_to_dl = db.get_urls_to_download()
                #urlinfo = urls_to_dl[0] if urls_to_dl else None
            with _worker_lock:
                if _end_threads_flag:
                    break
        with _worker_lock:
            if _end_threads_flag:
                log.info("hydownloader", "Stopping reverse lookup worker thread")
                _reverse_lookup_worker_ended_flag = True
                db.close_thread_connections()
        set_reverse_lookup_worker_status('shut down')
    except Exception as e:
        log.error("hydownloader", "Uncaught exception in reverse lookup worker thread", e)
        with _worker_lock:
            _reverse_lookup_worker_ended_flag = True
        db.close_thread_connections()
        shutdown()

def add_cors_headers() -> None:
    bottle.response.headers['Access-Control-Allow-Origin'] = '*'
    bottle.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
    bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, HyDownloader-Access-Key'

def check_access() -> None:
    if not db.get_conf("daemon.access_key") == bottle.request.headers.get("HyDownloader-Access-Key"):
        bottle.abort(403)

@route('/api_version', method='POST')
def route_api_version() -> dict:
    check_access()
    return {'version': constants.API_VERSION}

@route('/url_info', method='POST')
def route_url_info() -> str:
    check_access()
    result : list[dict] = []
    for url in bottle.request.json['urls']:
        sub_data = urls.subscription_data_from_url(url)
        url_info = {
            'queue_info': db.check_single_queue_for_url(url),
            'anchor_info': gallery_dl_utils.check_anchor_for_url(url),
            'known_url_info': db.get_known_urls(urls.urls_for_known_url_lookup(url)),
            'gallerydl_downloader': gallery_dl_utils.downloader_for_url(url),
            'sub_downloader': sub_data[0],
            'sub_keywords': sub_data[1],
            'existing_subscriptions': db.get_subscriptions_by_downloader_data(sub_data[0], sub_data[1])
        }
        result.append(url_info)
    return json.dumps(result)

@route('/subscription_data_to_url', method='POST')
def route_subscription_data_to_url() -> str:
    check_access()
    return {'url': urls.subscription_data_to_url(bottle.request.json['downloader'], bottle.request.json['keywords'], True)}

@route('/add_or_update_urls', method='POST')
def route_add_urls() -> dict:
    check_access()
    return {'status': db.add_or_update_urls(bottle.request.json)}

@route('/delete_urls', method='POST')
def route_delete_urls() -> dict:
    check_access()
    return {'status': db.delete_urls(bottle.request.json['ids'])}

@route('/get_queued_urls', method='POST')
def route_get_queued_urls() -> str:
    check_access()
    if 'from' in bottle.request.json and 'to' in bottle.request.json:
        try:
            range_from = int(bottle.request.json['from'])
            range_to = int(bottle.request.json['to'])
        except ValueError:
            return json.dumps([])
        return json.dumps(db.get_queued_urls_by_range(bottle.request.json.get("archived", False), (range_from, range_to)))
    if 'ids' in bottle.request.json:
        return json.dumps(db.get_queued_urls_by_id(bottle.request.json['ids'], archived = bottle.request.json.get("archived", False)))
    return json.dumps(db.get_queued_urls_by_range(bottle.request.json.get("archived", False)))

@route('/add_or_update_subscriptions', method='POST')
def route_add_or_update_subscriptions() -> dict:
    check_access()
    return {'status': db.add_or_update_subscriptions(bottle.request.json)}

@route('/add_or_update_subscription_checks', method='POST')
def route_add_or_update_subscription_checks() -> dict:
    check_access()
    return {'status': db.add_or_update_subscription_checks(bottle.request.json)}

@route('/add_or_update_missed_subscription_checks', method='POST')
def route_add_or_update_missed_subscription_checks() -> dict:
    check_access()
    return {'status': db.add_or_update_missed_subscription_checks(bottle.request.json)}

@route('/get_subscriptions', method='POST')
def route_get_subscriptions() -> str:
    check_access()
    if 'from' in bottle.request.json and 'to' in bottle.request.json:
        try:
            range_from = int(bottle.request.json['from'])
            range_to = int(bottle.request.json['to'])
        except ValueError:
            return json.dumps([])
        return json.dumps(db.get_subs_by_range((range_from, range_to)))
    if 'ids' in bottle.request.json:
        return json.dumps(db.get_subs_by_id(bottle.request.json['ids']))
    return json.dumps(db.get_subs_by_range())

@route('/get_subscription_checks', method='POST')
def route_get_subscription_checks() -> str:
    check_access()
    return json.dumps(db.get_subscription_checks(subscription_ids = bottle.request.json.get('ids', []), archived = bottle.request.json.get("archived", False)))

@route('/get_missed_subscription_checks', method='POST')
def route_get_missed_subscription_checks() -> str:
    check_access()
    return json.dumps(db.get_missed_subscription_checks(subscription_ids = bottle.request.json.get('ids', []), archived = bottle.request.json.get("archived", False)))

@route('/delete_subscriptions', method='POST')
def route_delete_subscriptions() -> dict:
    check_access()
    return {'status': db.delete_subscriptions(bottle.request.json['ids'])}

@route('/subscriptions_last_files', method='POST')
def route_subscriptions_last_files() -> str:
    check_access()
    result = []
    for i in bottle.request.json['ids']:
        result.append({
                'paths': db.get_last_files_for_sub(i)
            })
    return json.dumps(result)

@route('/urls_last_files', method='POST')
def route_urls_last_files() -> str:
    check_access()
    result = []
    for i in bottle.request.json['ids']:
        result.append({
                'paths': db.get_last_files_for_url(i)
            })
    return json.dumps(result)

@route('/get_status_info', method='POST')
def route_get_status_info() -> dict:
    check_access()
    with _status_lock:
        return {'subscriptions_due': len(db.get_due_subscriptions()), 'urls_queued': len(db.get_urls_to_download()),
                'subscriptions_paused': _sub_worker_paused_flag, 'urls_paused': _url_worker_paused_flag,
                'subscription_worker_status': _sub_worker_last_status, 'url_worker_status': _url_worker_last_status,
                'subscription_worker_last_update_time': _sub_worker_last_update_time, "url_worker_last_update_time": _url_worker_last_update_time}

@route('/set_cookies', method='POST')
def route_set_cookies() -> dict:
    check_access()
    if not os.path.isfile(db.get_rootpath()+"/cookies.txt"):
        return {'status': False}
    jar = ck.MozillaCookieJar(db.get_rootpath()+"/cookies.txt")
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except ck.LoadError:
        pass
    for c in bottle.request.json["cookies"]:
        name, value, domain, path, expires = c[0], c[1], c[2], c[3], c[4]
        #version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, expires, discard, comment, comment_url, rest
        cookie = ck.Cookie(0, name, value, None, False, domain, True, domain.startswith('.'), path, True, False, expires, False, None, None, {})
        jar.set_cookie(cookie)
    jar.save(ignore_discard=True, ignore_expires=True)
    return {'status': True}

@route('/pause_subscriptions', method='POST')
def route_pause_subscriptions() -> dict:
    global _sub_worker_paused_flag
    check_access()
    with _worker_lock:
        _sub_worker_paused_flag = True
    return {'status': True}

@route('/resume_subscriptions', method='POST')
def route_resume_subscriptions() -> dict:
    global _sub_worker_paused_flag
    check_access()
    with _worker_lock:
        _sub_worker_paused_flag = False
    return {'status': True}

@route('/pause_single_urls', method='POST')
def route_pause_single_urls() -> dict:
    global _url_worker_paused_flag
    check_access()
    with _worker_lock:
        _url_worker_paused_flag = True
    return {'status': True}

@route('/resume_single_urls', method='POST')
def route_resume_single_urls() -> dict:
    global _url_worker_paused_flag
    check_access()
    with _worker_lock:
        _url_worker_paused_flag = False
    return {'status': True}

@route('/run_tests', method='POST')
def route_run_tests() -> dict:
    check_access()
    return {'status': tools.test_internal(bottle.request.json['sites'])}

@route('/run_report', method='POST')
def route_run_report() -> dict:
    check_access()
    db.report(bottle.request.json['verbose'])
    return {'status': True}

@route('/shutdown', method='POST')
def route_shutdown() -> dict:
    global _shutdown_requested_by_api_thread
    check_access()
    _shutdown_requested_by_api_thread = True
    return {'status': True}

@route('/kill_current_sub', method='POST')
def route_kill_current_sub() -> dict:
    check_access()
    gallery_dl_utils.stop_process('sub worker')
    log.warning("hydownloader", "Current subscription check force-stopped via API")
    return {'status': True}

@route('/kill_current_url', method='POST')
def route_kill_current_url() -> dict:
    check_access()
    gallery_dl_utils.stop_process('url worker')
    log.warning("hydownloader", "Current URL download force-stopped via API")
    return {'status': True}

@route('/')
def route_index() -> str:
    return "hydownloader daemon"

# This route takes priority over all others. So any request with an OPTIONS method will be handled by this function.
@route('/<:re:.*>', method='OPTIONS')
def enable_cors_generic_route() -> None:
    add_cors_headers()

def path_is_parent(parent_path: str, child_path: str) -> bool:
    parent_path = os.path.abspath(parent_path)
    child_path = os.path.abspath(child_path)

    # Compare the common path of the parent and child path with the common path of just the parent path.
    # Using the commonpath method on just the parent path will regularise the path name in the same way as the comparison that deals with both paths,
    # removing any trailing path separator
    return os.path.commonpath([parent_path]) == os.path.commonpath([parent_path, child_path])

@route('/<filename:re:.*>', method='GET')
def route_serve_file(filename: str):
    check_access()
    fullpath = db.get_rootpath() + '/' + filename
    if os.path.isfile(fullpath):
        if not path_is_parent(db.get_rootpath(), fullpath):
            log.warning("hydownloader", f"Request received for file outside database rootpath: {fullpath}")
            bottle.abort(403)
        return bottle.static_file(filename, root=db.get_rootpath())
    bottle.abort(404)

# This executes after every route. We use it to attach CORS headers when applicable.
@hook('after_request')
def enable_cors_after_request_hook() -> None:
    add_cors_headers()

@click.group()
def cli() -> None:
    pass

def api_worker(path: str, debug: bool) -> None:
    global _srv
    try:
        if db.get_conf('daemon.ssl') and os.path.isfile(path+"/server.pem"):
            log.info("hydownloader", "Starting daemon (with SSL)...")
            _srv = SSLWSGIRefServer(path+"/server.pem", host=db.get_conf('daemon.host'), port=db.get_conf('daemon.port'))
            bottle.run(server=_srv, debug=debug)
        else:
            if db.get_conf('daemon.ssl'):
                log.warning("hydownloader", "SSL enabled in config, but no server.pem file found in the db folder, continuing without SSL...")
            log.info("hydownloader", "Starting daemon...")
            _srv = SSLWSGIRefServer("", host=db.get_conf('daemon.host'), port=db.get_conf('daemon.port'))
            bottle.run(server=_srv, debug=debug)
    except OSError as e:
        log.error("hydownloader", "Error while trying to run API server. Maybe the port is already in use?", e)
        shutdown()

@cli.command(help='Start the hydownloader daemon with the given data path.')
@click.option('--path', type=str, required=True, help='The folder where hydownloader should store its database and the downloaded files.')
@click.option('--debug', type=bool, default=False, show_default=True, is_flag=True, help='Enable additional debug logging.')
@click.option('--no-sub-worker', type=bool, default=False, show_default=True, is_flag=True, help='Do not start subscription worker thread.')
@click.option('--no-url-worker', type=bool, default=False, show_default=True, is_flag=True, help='Do not start single URL queue worker thread.')
@click.option('--no-reverse-lookup-worker', type=bool, default=False, show_default=True, is_flag=True, help='Do not start reverse lookup worker thread.')
def start(path : str, debug : bool, no_sub_worker: bool, no_url_worker: bool, no_reverse_lookup_worker: bool) -> None:
    log.init(path, debug)
    db.init(path)

    output_postprocessors.process_additional_data()
    output_postprocessors.parse_log_files()

    if not no_sub_worker:
        subs_thread = threading.Thread(target=subscription_worker, name='Subscription worker', daemon=True)
        subs_thread.start()

    if not no_url_worker:
        url_thread = threading.Thread(target=url_queue_worker, name='Single URL queue worker', daemon=True)
        url_thread.start()

    if not no_reverse_lookup_worker:
        lookup_thread = threading.Thread(target=reverse_lookup_worker, name='Reverse lookup worker', daemon=True)
        lookup_thread.start()

    api_thread = threading.Thread(target=api_worker, args=(path, debug))
    api_thread.start()

    while not _shutdown_started and not _shutdown_requested_by_api_thread:
        time.sleep(1)
    shutdown()

def shutdown() -> None:
    global _shutdown_started
    db.close_thread_connections()
    if _shutdown_started: return
    _shutdown_started = True
    end_downloader_threads()
    if _srv:
        _srv.stop()
    db.shutdown()
    try:
        log.info("hydownloader", "hydownloader shut down")
    except RuntimeError:
        pass
    sys.stderr.close()
    os._exit(0)

def main() -> None:
    atexit.register(shutdown)
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    signal.signal(signal.SIGINT, lambda signum, frame: shutdown())
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown())

    bottle.BaseRequest.MEMFILE_MAX *= 1000

    cli()
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()

if __name__ == "__main__":
    main()
