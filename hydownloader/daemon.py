#!/usr/bin/env python3

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
from hydownloader import db, log, gallery_dl_utils, urls, __version__, uri_normalizer, tools, constants, output_postprocessors

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

_worker_lock = threading.Lock()
_status_lock = threading.Lock()
_end_threads_flag = False
_sub_worker_ended_flag = True
_url_worker_ended_flag = True
_sub_worker_paused_flag = False
_url_worker_paused_flag = False
_shutdown_started = False
_url_worker_last_status = "no information"
_sub_worker_last_status = "no information"
_url_worker_last_update_time : float = 0
_sub_worker_last_update_time : float = 0

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

def end_threads() -> None:
    global _end_threads_flag
    with _worker_lock:
        _end_threads_flag = True
    while not (_sub_worker_ended_flag and _url_worker_ended_flag):
        time.sleep(1)

def subscription_worker() -> None:
    global _sub_worker_ended_flag
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
                log.info(f"subscription-{sub['id']}", status_msg.capitalize())
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
                    max_file_count = sub['max_files_initial'] if initial_check else sub['max_files_regular']
                    )
                if result:
                    log.warning(f"subscription-{sub['id']}", "Error: "+result)
                else:
                    sub['last_successful_check'] = check_started_time
                sub['last_check'] = check_started_time
                new_files, skipped_files = output_postprocessors.process_additional_data(subscription_id = sub['id'])
                output_postprocessors.parse_log_files()
                check_ended_time = time.time()
                db.add_subscription_check(sub['id'], new_files=new_files, already_seen_files=skipped_files, time_started=check_started_time, time_finished=check_ended_time, status=result if result else 'ok')
                db.add_or_update_subscriptions([sub])
                status_msg = f"finished checking subscription: {sub['id']} (downloader: {sub['downloader']}, keywords: {sub['keywords']}), new files: {new_files}, skipped: {skipped_files}"
                set_subscription_worker_status(status_msg)
                log.info(f"subscription-{sub['id']}", status_msg.capitalize())
                subs_due = db.get_due_subscriptions()
                sub = subs_due[0] if subs_due else None
            with _worker_lock:
                if _end_threads_flag:
                    break
        with _worker_lock:
            if _end_threads_flag:
                log.info("hydownloader", "Stopping subscription worker thread")
                _sub_worker_ended_flag = True
    except Exception as e:
        log.fatal("hydownloader", "Uncaught exception in subscription worker thread", e)
        shutdown()

def url_queue_worker() -> None:
    global _url_worker_ended_flag
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
                log.info("single url downloader", status_msg.capitalize())
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
                    max_file_count = urlinfo['max_files']
                    )
                if result:
                    log.warning("single url downloader", f"Error while downloading {urlinfo['url']}: {result}")
                    urlinfo['status'] = 1
                    urlinfo['status_text'] = result
                else:
                    urlinfo['status'] = 0
                    urlinfo['status_text'] = 'ok'
                urlinfo['time_processed'] = check_time
                new_files, skipped_files = output_postprocessors.process_additional_data(url_id = urlinfo['id'])
                output_postprocessors.parse_log_files()
                urlinfo['new_files'] = new_files
                urlinfo['already_seen_files'] = skipped_files
                db.add_or_update_urls([urlinfo])
                status_msg = f"finished checking URL: {urlinfo['url']}, new files: {new_files}, skipped: {skipped_files}"
                set_url_worker_status(status_msg)
                log.info("single url downloader", status_msg.capitalize())
                urls_to_dl = db.get_urls_to_download()
                urlinfo = urls_to_dl[0] if urls_to_dl else None
            with _worker_lock:
                if _end_threads_flag:
                    break
        with _worker_lock:
            if _end_threads_flag:
                log.info("hydownloader", "Stopping single URL queue worker thread")
                _url_worker_ended_flag = True
    except Exception as e:
        log.fatal("hydownloader", "Uncaught exception in URL worker thread", e)
        shutdown()

def add_cors_headers() -> None:
    bottle.response.headers['Access-Control-Allow-Origin'] = '*'
    bottle.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
    bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

def check_access() -> None:
    if not db.get_conf("daemon.access_key") == bottle.request.headers.get("HyDownloader-Access-Key"):
        bottle.abort(403)

@route('/api_version', method='POST')
def route_api_version() -> dict:
    check_access()
    return {'version': constants.API_VERSION}

@route('/url_history_info', method='POST')
def route_url_history_info() -> str:
    check_access()
    result = []
    for url in bottle.request.json['urls']:
        url_info = {'url': url, 'normalized_url': uri_normalizer.normalizes(url)}
        url_info['queue_info'] = db.check_single_queue_for_url(url)
        url_info['anchor_info'] = gallery_dl_utils.check_anchor_for_url(url)
        result.append(url_info)
    return json.dumps(result)

@route('/check_urls', method='POST')
def route_check_urls() -> str:
    check_access()
    result : list[dict] = []
    for url in bottle.request.json['urls']:
        url_info = {'url': url, 'normalized_url': uri_normalizer.normalizes(url)}
        url_info['downloader'] = gallery_dl_utils.downloader_for_url(url)
        sub_data = urls.subscription_data_from_url(url)
        existing_subs = []
        for sub in sub_data:
            existing_subs += db.get_subscriptions_by_downloader_data(sub[0], sub[1])
        url_info['existing_subscriptions'] = existing_subs
    return json.dumps(result)

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
    return json.dumps(db.get_subscription_checks(subscription_id = bottle.request.json['subscription_id'], archived = bottle.request.json.get("archived", False)))

@route('/delete_subscriptions', method='POST')
def route_delete_subscriptions() -> dict:
    check_access()
    return {'status': db.delete_subscriptions(bottle.request.json['ids'])}

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
    jar.load(ignore_discard=True, ignore_expires=True)
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
def route_shutdown() -> None:
    check_access()
    shutdown()

@route('/')
def route_index() -> str:
    return "hydownloader daemon"

# This route takes priority over all others. So any request with an OPTIONS method will be handled by this function.
@route('/<:re:.*>', method='OPTIONS')
def enable_cors_generic_route() -> None:
    add_cors_headers()

@route('/<filename:re:.*>', method='GET')
def route_serve_file(filename: str):
    check_access()
    if os.path.isfile(db.get_rootpath() + '/' + filename):
        return bottle.static_file(filename, root=db.get_rootpath())
    bottle.abort(404)

# This executes after every route. We use it to attach CORS headers when applicable.
@hook('after_request')
def enable_cors_after_request_hook() -> None:
    add_cors_headers()

@click.group()
def cli() -> None:
    pass

@cli.command(help='Start the hydownloader daemon with the given data path.')
@click.option('--path', type=str, required=True, help='The folder where hydownloader should store its database and the downloaded files.')
@click.option('--debug', type=bool, default=False, is_flag=True, help='Enable additional debug logging.')
def start(path : str, debug : bool) -> None:
    log.init(path, debug)
    db.init(path)

    output_postprocessors.process_additional_data()
    output_postprocessors.parse_log_files()

    subs_thread = threading.Thread(target=subscription_worker, name='Subscription worker', daemon=True)
    subs_thread.start()

    url_thread = threading.Thread(target=url_queue_worker, name='Single URL queue worker', daemon=True)
    url_thread.start()

    if db.get_conf('daemon.ssl') and os.path.isfile(path+"/server.pem"):
        log.info("hydownloader", "Starting daemon (with SSL)...")
        srv = SSLWSGIRefServer(path+"/server.pem", host=db.get_conf('daemon.host'), port=db.get_conf('daemon.port'))
        bottle.run(server=srv, debug=debug)
    else:
        if db.get_conf('daemon.ssl'):
            log.warning("hydownloader", "SSL enabled in config, but no server.pem file found in the db folder, continuing without SSL...")
        log.info("hydownloader", "Starting daemon...")
        srv = SSLWSGIRefServer("", host=db.get_conf('daemon.host'), port=db.get_conf('daemon.port'))
        bottle.run(server=srv, debug=debug)

def shutdown() -> None:
    global _shutdown_started
    if _shutdown_started: return
    _shutdown_started = True
    end_threads()
    db.shutdown()
    try:
        log.info("hydownloader", "hydownloader shut down")
    except RuntimeError:
        pass
    sys.stderr.close()
    os._exit(0)

def main() -> None:
    atexit.register(shutdown)
    signal.signal(signal.SIGINT, lambda signum, frame: shutdown())
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown())

    cli()
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()

if __name__ == "__main__":
    main()
