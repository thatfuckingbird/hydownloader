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

import shutil
import os
import sys
import random
import datetime
import sqlite3
import time
import signal
import subprocess
import re
import urllib.parse
import requests
from http.cookiejar import MozillaCookieJar
from typing import Optional
import click
from hydownloader import db, log, gallery_dl_utils, output_postprocessors, urls

@click.group()
def cli() -> None:
    pass

def clear_test_env() -> None:
    log.info('hydownloader-test', 'Clearing test environment...')
    if os.path.exists(db.get_rootpath()+'/test'):
        shutil.rmtree(db.get_rootpath()+'/test')
    os.makedirs(db.get_rootpath() + "/test")
    log.info('hydownloader-test', 'Test environment cleared')

def check_results_of_post_url(data: dict, sitename: str) -> bool:
    """
    Downloads a URL with gallery-dl, then checks if the
    downloaded filenames, file content and anchor entries match what was provided by the caller.
    """
    url = data['url']
    filenames = data['filenames']
    anchors = data['anchors']
    log.info("hydownloader-test", f'Testing downloading of posts for site {sitename}')
    log_file = db.get_rootpath()+f"/logs/test-site-{sitename}-gallery-dl.txt"
    result_txt = gallery_dl_utils.run_gallery_dl(
        url=url,
        ignore_anchor=False,
        metadata_only=False,
        log_file=log_file,
        console_output_file=db.get_rootpath()+f"/test/test-site-{sitename}-gallery-dl-output.txt",
        unsupported_urls_file=db.get_rootpath()+f"/test/test-site-{sitename}-unsupported-urls-gallery-dl.txt",
        overwrite_existing=False,
        subscription_mode=False,
        test_mode = True
    )
    result = True
    if result_txt:
        log.error("hydownloader-test", f"Error returned for {sitename} download: {result_txt}")
        result = False
    else:
        log.info("hydownloader-test", f"Return code for {sitename} download OK")
    for fname in filenames:
        abs_fname = db.get_rootpath()+"/test/data/gallery-dl/"+fname
        if not os.path.isfile(abs_fname):
            log.error("hydownloader-test", f"Missing expected file: {fname}")
            result = False
        else:
            log.info("hydownloader-test", f"Found expected file: {fname}")
            for content in filenames[fname]:
                with open(abs_fname, encoding='utf-8-sig') as f:
                    if content in f.read():
                        log.info("hydownloader-test", "Expected file content found")
                    else:
                        log.error("hydownloader-test", f"Expected file content ({content}) NOT found")
                        result = False
    conn = sqlite3.connect(db.get_rootpath()+"/test/anchor.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    for anchor in anchors:
        try:
            c.execute('select entry from archive where entry = ?', (anchor,))
            if len(c.fetchall()):
                log.info("hydownloader-test", f"Expected anchor {anchor} found in database")
            else:
                log.error("hydownloader-test", f"Expected anchor {anchor} NOT found in database")
                result = False
        except sqlite3.OperationalError as e:
            log.error("hydownloader-test", "Error while trying to query anchor database - download failed?", e)
            result = False
    return result

@cli.command(help='Print information about subscriptions with missed subscription checks.')
@click.option('--path', type=str, required=True, help='Database path.')
@click.option('--reason', type=int, required=True, help='Filter missed subscription checks by reason (0-2, see the docs).')
@click.option('--only-urls', type=bool, is_flag=True, required=False, default=False, show_default=True, help='Only print URLs.')
def subs_with_missed_checks(path: str, reason: int, only_urls: bool):
    log.init(path, True)
    db.init(path)
    checks = db.get_missed_subscription_checks([], False)
    sub_ids = set()
    for check in checks:
        if check['reason'] == reason: sub_ids.add(check['subscription_id'])
    subs = db.get_subs_by_id(list(sub_ids))
    log.info("hydownloader-tools", f"List of subscriptions with missed checks (reason={reason}, count={len(sub_ids)}):")
    for sub in subs:
        url = urls.subscription_data_to_url(sub['downloader'], sub['keywords'])
        if only_urls:
            log.info("hydownloader-tools", url)
        else:
            log.info("hydownloader-tools", f"{sub['id']} {sub['downloader']} {sub['keywords']} {url}")

@cli.command(help='Test downloading from a list of sites.')
@click.option('--path', type=str, required=True, help='Database path.')
@click.option('--sites', type=str, required=True, help='A comma-separated list of sites to test downloading from. Currently supported: environment, gelbooru, pixiv, lolibooru, patreon, danbooru, 3dbooru, nijie, sankaku, idolcomplex, artstation, twitter, deviantart, webtoons, baraag, pawoo, yandere, hentaifoundry, rule34, e621, furaffinity, instagram. WARNING: this will attempt to download "sensitive" content.')
def test(path: str, sites: str) -> None:
    log.init(path, True)
    db.init(path)
    if not test_internal(sites):
        sys.exit(1)

def test_internal(sites: str) -> bool:
    post_url_data = {
        'gelbooru': {
            'url': "https://gelbooru.com/index.php?page=post&s=view&id=6002236",
            'filenames': {
                "gelbooru/gelbooru_6002236_0ef507cc4c222406da544db3231de323.jpg.json": ["1girl ", "wings", '"rating": "questionable"', '"tags_general":'],
                "gelbooru/gelbooru_6002236_0ef507cc4c222406da544db3231de323.jpg": []
            },
            'anchors': ["gelbooru6002236"]
        },
        'gelbooru_notes': {
            'url': "https://gelbooru.com/index.php?page=post&s=view&id=5997331",
            'filenames': {
                "gelbooru/gelbooru_5997331_7726d401af0e6bf5b58809f65d08334e.png.json": ['"y": 72', '"x": 35', '"width": 246', '"height": 553', '"body": "Look over this way when you talk~"']
            },
            'anchors': ["gelbooru5997331"]
        },
        'danbooru': {
            'url': "https://danbooru.donmai.us/posts/4455434",
            'filenames': {
                "danbooru/danbooru_4455434_e110444217827ef3f82fb33b45e1841f.png.json": ["1girl ", "tail", '"rating": "q"'],
                "danbooru/danbooru_4455434_e110444217827ef3f82fb33b45e1841f.png": []
            },
            'anchors': ["danbooru4455434"]
        },
        'pixiv': {
            'url': "https://www.pixiv.net/en/artworks/98309573",
            'filenames': {
                "pixiv/39123643 zurimoku/98309573_p1.jpg.json": [],
                "pixiv/39123643 zurimoku/98309573_p0.jpg.json": ['"name": "Belko"'],
                "pixiv/39123643 zurimoku/98309573_p1.jpg": [],
                "pixiv/39123643 zurimoku/98309573_p0.jpg": []
            },
            'anchors': ["pixiv98309573_p00","pixiv98309573_p01"]
        },
        'pixiv_ugoira': {
            'url': "https://www.pixiv.net/en/artworks/88748768",
            'filenames': {
                "pixiv/9313418 thaimay704/88748768_p0.zip": [],
                "pixiv/9313418 thaimay704/88748768_p0.zip.json": [],
                "pixiv/9313418 thaimay704/88748768_p0.webm": []
            },
            'anchors': ["pixiv88748768"]
        },
        'lolibooru': {
            'url': 'https://lolibooru.moe/post/show/178123/1girl-barefoot-brown_eyes-brown_hair-cameltoe-cove',
            'filenames': {
                "lolibooru/lolibooru_178123_a77d70e0019fc77c25d0ae563fc9b324.jpg.json": ["1girl ", " swimsuit", '"rating": "q",'],
                "lolibooru/lolibooru_178123_a77d70e0019fc77c25d0ae563fc9b324.jpg": []
            },
            'anchors': ["lolibooru178123"]
        },
        '3dbooru': {
            'url': "http://behoimi.org/post/show/648363/apron-black_legwear-collar-cosplay-hairband-immora",
            'filenames': {
                "3dbooru/3dbooru_648363_720f344170696293c3fe2640c59d8f41.jpg.json": ["cosplay ", " maid_uniform", '"rating": "s",'],
                "3dbooru/3dbooru_648363_720f344170696293c3fe2640c59d8f41.jpg": []
            },
            'anchors': ["3dbooru648363"]
        },
        'nijie': {
            'url': "https://nijie.info/view.php?id=306993",
            'filenames': {
                "nijie/72870/306993_p0.jpg": [],
                "nijie/72870/306993_p1.jpg": [],
                "nijie/72870/306993_p0.jpg.json": [],
                "nijie/72870/306993_p1.jpg.json": ["\"オリジナル\"", "\"title\": \"朝7時50分の通学路\","]
            },
            'anchors': ["nijie306993_0", "nijie306993_1"]
        },
        'patreon': {
            'url': "https://www.patreon.com/posts/new-cg-set-on-48042243",
            'filenames': {
                "patreon/Osiimi Chan/48042243_NEW CG SET on Gumroad!! Ganyu's Hypnotic Rendezvou_01.png": []
            },
            'anchors': ["patreon48042243_1"]
        },
        'sankaku': {
            'url': "https://chan.sankakucomplex.com/post/show/707246",
            'filenames': {
                "sankaku/sankaku_707246_5da41b5136905c35cad9cbcba89836a3.jpg": [],
                "sankaku/sankaku_707246_5da41b5136905c35cad9cbcba89836a3.jpg.json": ['"kirisame_marisa"', '"3girls"']
            },
            'anchors': ["sankaku707246"]
        },
        'idolcomplex': {
            'url': "https://idol.sankakucomplex.com/post/show/701724",
            'filenames': {
                "idolcomplex/idolcomplex_701724_92b853bcf8dbff393c6217839013bcab.jpg": [],
                "idolcomplex/idolcomplex_701724_92b853bcf8dbff393c6217839013bcab.jpg.json": ['"rating": "q",', 'nikumikyo,']
            },
            'anchors': ["idolcomplex701724"]
        },
        'artstation': {
            'url': "https://www.artstation.com/artwork/W2LROD",
            'filenames': {
                "artstation/sergey_vasnev/artstation_6721469_24728858_Procession.jpg": [],
                "artstation/sergey_vasnev/artstation_6721469_24728858_Procession.jpg.json": ['"title": "Procession",']
            },
            'anchors': ["artstation6721469"]
        },
        'deviantart': {
            'url': "https://www.deviantart.com/squchan/art/Atelier-Ryza-820511154",
            'filenames': {
                "deviantart/SquChan/deviantart_820511154_Atelier Ryza.jpg": [],
                "deviantart/SquChan/deviantart_820511154_Atelier Ryza.jpg.json": ['"is_mature": true,']
            },
            'anchors': ["deviantart820511154"]
        },
        'twitter': {
            'url': "https://twitter.com/momosuzunene/status/1380033327680266244",
            'filenames': {
                "twitter/momosuzunene/1380033327680266244_1.jpg": [],
                "twitter/momosuzunene/1380033327680266244_1.jpg.json": ['"name": "momosuzunene",']
            },
            'anchors': ["twitter1380033327680266244_1"]
        },
        'webtoons': {
            'url': "https://www.webtoons.com/en/challenge/crawling-dreams/ep-1-nyarla-ghast/viewer?title_no=141539&episode_no=81",
            'anchors': ['webtoons141539_1_1','webtoons141539_1_2','webtoons141539_1_3','webtoons141539_1_4'],
            'filenames': {
                "webtoons/crawling-dreams/81-01.jpg": [],
                "webtoons/crawling-dreams/81-01.jpg.json": ['"comic": "crawling-dreams"']
            }
        },
        'baraag': {
            'url': "https://baraag.net/@pumpkinnsfw/106191173043385531",
            'anchors': ['baraag106191173043385531_106191139078112401','baraag106191173043385531_106191139927706653'],
            'filenames': {
                "mastodon/baraag.net/pumpkinnsfw/baraag_106191173043385531_106191139078112401.png": [],
                "mastodon/baraag.net/pumpkinnsfw/baraag_106191173043385531_106191139078112401.png.json": ['"sensitive": true']
            }
        },
        'pawoo': {
            'url': "https://pawoo.net/@e050f256/101408660499763258",
            'anchors': ['pawoo101408660499763258_11289545','pawoo101408660499763258_11289548'],
            'filenames': {
                "mastodon/pawoo.net/e050f256/pawoo_101408660499763258_11289548.png": [],
                "mastodon/pawoo.net/e050f256/pawoo_101408660499763258_11289545.png": [],
                "mastodon/pawoo.net/e050f256/pawoo_101408660499763258_11289548.png.json": ['"sensitive": false,'],
                "mastodon/pawoo.net/e050f256/pawoo_101408660499763258_11289545.png.json": []
            }
        },
        'hentaifoundry': {
            'url': "https://www.hentai-foundry.com/pictures/user/PalomaP/907277/Rapunzel-loves-creampie",
            'anchors': ["hentaifoundry907277"],
            'filenames': {
                "hentaifoundry/PalomaP/hentaifoundry_907277_Rapunzel loves creampie.jpg": [],
                "hentaifoundry/PalomaP/hentaifoundry_907277_Rapunzel loves creampie.jpg.json": ['"tags": [','"creampie"']
            }
        },
        'yandere': {
            'url': "https://yande.re/post/show/619304",
            'anchors': ["yandere619304"],
            'filenames': {
                'yandere/yandere_619304_449a208b7a42f917498a00386e173118.jpg': [],
                'yandere/yandere_619304_449a208b7a42f917498a00386e173118.jpg.json': ['"tags_artist": "zuima"']
            }
        },
        'rule34': {
            'url': "https://rule34.xxx/index.php?page=post&s=view&id=4085100",
            'anchors': ["rule344085100"],
            'filenames': {
                'rule34/rule34_4085100_230c488b6784beb15f0278f6a6ce2a93.jpg': [],
                'rule34/rule34_4085100_230c488b6784beb15f0278f6a6ce2a93.jpg.json': ['"tags_artist": "methados"']
            }
        },
        'e621': {
            'url': "https://e621.net/posts/1766367",
            'anchors': ["e6211766367"],
            'filenames': {
                'e621/e621_1766367_441725945326e0fa7a3f21978cb38ded.jpg': [],
                'e621/e621_1766367_441725945326e0fa7a3f21978cb38ded.jpg.json': ['"id": 1766367'],
            }
        },
        'furaffinity': {
            'url': "https://www.furaffinity.net/view/45398142/",
            'anchors': ["furaffinity45398142"],
            'filenames': {
                'furaffinity/bermasin/45398142.jpg': [],
                'furaffinity/bermasin/45398142.jpg.json': ['"artist": "bermasin"']
            }
        },
        'instagram': {
            'url': "https://www.instagram.com/p/CdYF0WmuDnm/",
            'filenames': {
                "instagram/gigihadid/2835041553347000806_2835041547869314463.jpg": [],
                "instagram/gigihadid/2835041553347000806_2835041547869314463.jpg.json": ['"username": "gigihadid",']
            },
            'anchors': ["instagram2835041547869314463"]
        }
    }

    sites_done = set()
    for site in sites.split(','):
        site = site.strip()
        if site in sites_done:
            continue
        sites_done.add(site)
        clear_test_env()
        log_file = db.get_rootpath()+f"/logs/test-site-{site}-gallery-dl.txt"
        should_break = False
        if site == 'environment':
            log.info("hydownloader-test", f"Python version: {sys.version}")
            log.info("hydownloader-test", "Querying gallery-dl version")
            version_str = gallery_dl_utils.run_gallery_dl_with_custom_args(['--version'], capture_output = True).stdout.strip()
            try:
                if version_str.endswith("-dev"): version_str = version_str[:-4]
                major, minor, patch = tuple(map(int, version_str.split('.')))
                if major != 1 or minor == 23 and patch < 3:
                    log.error('hydownloader-test', f"Bad gallery-dl version: {version_str}, need 1.23.3 or newer")
                    should_break = True
                else:
                    log.info('hydownloader-test', f"Found gallery-dl version: {version_str}, this is OK")
            except ValueError as e:
                log.error('hydownloader-test', "Could not recognize gallery-dl version", e)
                should_break = True
            try:
                ff_result = subprocess.run(['ffmpeg', '-version'], capture_output = True, text = True, check = False).stdout.split('\n')[0]
                log.info('hydownloader-test', f"Found ffmpeg version: {ff_result}")
            except FileNotFoundError as e:
                log.error('hydownloader-test', "Could not find ffmpeg", e)
                should_break = True
            try:
                yt_result = subprocess.run(['yt-dlp', '--version'], capture_output = True, text = True, check = False).stdout.strip()
                log.info('hydownloader-test', f"Found yt-dlp version: {yt_result}")
            except FileNotFoundError as e:
                log.error('hydownloader-test', "Could not find yt-dlp", e)
                should_break = True
        elif site == "gelbooru":
            log.info("hydownloader-test", "Testing gelbooru...")

            log.info("hydownloader-test", 'Testing search of "sensitive" content')
            sensitive_url = "https://gelbooru.com/index.php?page=post&s=list&tags=loli"
            result = gallery_dl_utils.run_gallery_dl_with_custom_args([sensitive_url, '--get-urls', '-o', 'image-range="1-10"', '--write-log', log_file], capture_output = True)
            sensitive_ok = True
            if result.returncode != 0:
                status_txt = gallery_dl_utils.check_return_code(result.returncode)
                log.error("hydownloader-test", f'Error returned while trying to download "sensitive" content: return code {result.returncode}, {status_txt}')
                sensitive_ok = False
                should_break = True
            sensitive_results_cnt = len(re.findall("https://.*?gelbooru.com/images", result.stdout))
            if sensitive_results_cnt < 10:
                log.error("hydownloader-test", f'Failed to find "sensitive" content, insufficient number of results: {sensitive_results_cnt}')
                sensitive_ok = False
                should_break = True
            if sensitive_ok:
                log.info("hydownloader-test", 'Search of "sensitive" content seems to be working OK')

            should_break = not check_results_of_post_url(post_url_data['gelbooru'], site) or should_break

            log.info("hydownloader-test", 'Testing note extraction')
            should_break = not check_results_of_post_url(post_url_data['gelbooru_notes'], site) or should_break
        elif site == "danbooru":
            log.info("hydownloader-test", "Testing danbooru...")

            log.info("hydownloader-test", 'Testing search of "sensitive" content')
            sensitive_url = "https://danbooru.donmai.us/posts?tags=loli"
            result = gallery_dl_utils.run_gallery_dl_with_custom_args([sensitive_url, '--get-urls', '-o', 'image-range="1-10"', '--write-log', log_file], capture_output = True)
            sensitive_ok = True
            if result.returncode != 0:
                status_txt = gallery_dl_utils.check_return_code(result.returncode)
                log.error("hydownloader-test", f'Error returned while trying to download "sensitive" content: return code {result.returncode}, {status_txt}')
                sensitive_ok = False
                should_break = True
            sensitive_results_cnt = len(re.findall("https://cdn.donmai.us/", result.stdout))
            if sensitive_results_cnt < 10:
                log.error("hydownloader-test", f'Failed to find "sensitive" content, insufficient number of results: {sensitive_results_cnt}')
                sensitive_ok = False
                should_break = True
            if sensitive_ok:
                log.info("hydownloader-test", 'Search of "sensitive" content seems to be working OK')

            should_break = not check_results_of_post_url(post_url_data['danbooru'], site) or should_break
        elif site == "pixiv":
            log.info("hydownloader-test", "Testing pixiv...")
            should_break = not check_results_of_post_url(post_url_data['pixiv'], site) or should_break
            log.info("hydownloader-test", 'Testing downloading of ugoira')
            should_break = not check_results_of_post_url(post_url_data['pixiv_ugoira'], site) or should_break
        elif site == "lolibooru":
            log.info("hydownloader-test", "Testing lolibooru.moe...")
            should_break = not check_results_of_post_url(post_url_data['lolibooru'], site) or should_break
        elif site == "3dbooru":
            log.info("hydownloader-test", "Testing 3dbooru...")
            should_break = not check_results_of_post_url(post_url_data['3dbooru'], site) or should_break
        elif site == "patreon":
            log.info("hydownloader-test", "Testing patreon...")
            should_break = not check_results_of_post_url(post_url_data['patreon'], site) or should_break
        elif site == "nijie":
            log.info("hydownloader-test", "Testing nijie.info...")
            should_break = not check_results_of_post_url(post_url_data['nijie'], site) or should_break
        elif site == "sankaku":
            log.info("hydownloader-test", "Testing sankaku...")
            should_break = not check_results_of_post_url(post_url_data['sankaku'], site) or should_break
        elif site == "idolcomplex":
            log.info("hydownloader-test", "Testing idolcomplex...")
            should_break = not check_results_of_post_url(post_url_data['idolcomplex'], site) or should_break
        elif site == "artstation":
            log.info("hydownloader-test", "Testing artstation...")
            should_break = not check_results_of_post_url(post_url_data['artstation'], site) or should_break
        elif site == "twitter":
            log.info("hydownloader-test", "Testing twitter...")
            should_break = not check_results_of_post_url(post_url_data['twitter'], site) or should_break
        elif site == "deviantart":
            log.info("hydownloader-test", "Testing deviantart...")
            should_break = not check_results_of_post_url(post_url_data['deviantart'], site) or should_break
        elif site == "webtoons":
            log.info("hydownloader-test", "Testing webtoons...")
            should_break = not check_results_of_post_url(post_url_data['webtoons'], site) or should_break
        elif site == "baraag":
            log.info("hydownloader-test", "Testing baraag...")
            should_break = not check_results_of_post_url(post_url_data['baraag'], site) or should_break
        elif site == "pawoo":
            log.info("hydownloader-test", "Testing pawoo...")
            should_break = not check_results_of_post_url(post_url_data['pawoo'], site) or should_break
        elif site == "hentaifoundry":
            log.info("hydownloader-test", "Testing hentaifoundry...")
            should_break = not check_results_of_post_url(post_url_data['hentaifoundry'], site) or should_break
        elif site == "yandere":
            log.info("hydownloader-test", "Testing yande.re...")
            should_break = not check_results_of_post_url(post_url_data['yandere'], site) or should_break
        elif site == "rule34":
            log.info("hydownloader-test", "Testing rule34.xxx...")
            should_break = not check_results_of_post_url(post_url_data['rule34'], site) or should_break
        elif site == "e621":
            log.info("hydownloader-test", "Testing e621.net...")
            should_break = not check_results_of_post_url(post_url_data['e621'], site) or should_break
        elif site == "furaffinity":
            log.info("hydownloader-test", "Testing furaffinity.net...")
            should_break = not check_results_of_post_url(post_url_data['furaffinity'], site) or should_break
        elif site == "instagram":
            log.info("hydownloader-test", "Testing instagram...")
            should_break = not check_results_of_post_url(post_url_data['instagram'], site) or should_break
        else:
            log.error("hydownloader-test", f"Site name not recognized: {site}, no testing done")
            return False
        if should_break:
            log.error("hydownloader-test", f"Stopping early due to errors while testing {site}, test environment kept for inspection")
            return False
        clear_test_env()
    return True

@cli.command(help='Print a report about subscriptions and the URL queue, with a focus on finding dead, failing or erroneous subscriptions/URLs.')
@click.option('--path', type=str, required=True, help='Database path.')
@click.option('--verbose', type=bool, is_flag=True, required=False, default=False, show_default=True, help='More details (listing individual subscriptions/URLs, not just aggregate numbers). Might produce a lot of output.')
@click.option('--no-urls', type=bool, is_flag=True, required=False, default=False, show_default=True, help='Only report about subscriptions, not single URL downloads.')
@click.option('--include-archived', type=bool, is_flag=True, required=False, default=False, show_default=True, help='Include archived URL entries in the statistics.')
@click.option('--include-paused', type=bool, is_flag=True, required=False, default=False, show_default=True, help='Include paused subscriptions in the statistics.')
def report(path: str, verbose: bool, no_urls: bool, include_archived: bool, include_paused: bool) -> None:
    log.init(path, True)
    db.init(path)
    db.report(verbose, not no_urls, include_archived)

@cli.command(help='Acquire OAuth token needed for Pixiv.')
@click.option('--path', type=str, required=True, help='Database path.')
def pixiv_login(path: str) -> None:
    log.init(path, True)
    db.init(path)
    args = ['--cookies', db.get_rootpath()+'/cookies.txt']
    args += ['-o', 'cache.file='+db.get_rootpath()+'/gallery-dl-cache.db']
    args += ['oauth:pixiv']
    gallery_dl_utils.run_gallery_dl_with_custom_args(args)

@cli.command(help='Acquire OAuth token needed for deviantart.')
@click.option('--path', type=str, required=True, help='Database path.')
def deviantart_login(path: str) -> None:
    log.init(path, True)
    db.init(path)
    args = ['--cookies', db.get_rootpath()+'/cookies.txt']
    args += ['-o', 'cache.file='+db.get_rootpath()+'/gallery-dl-cache.db']
    args += ['oauth:deviantart']
    gallery_dl_utils.run_gallery_dl_with_custom_args(args)

@cli.command(help='Initialize hydownloader database folder.')
@click.option('--path', type=str, required=True, help='Database path.')
def init_db(path: str) -> None:
    log.init(path, True)
    db.init(path)

@cli.command(help='Rotate the main daemon log.')
@click.option('--path', type=str, required=True, help='Database path.')
def rotate_daemon_log(path: str) -> None:
    log.init(path, True)
    db.init(path)
    log.rotate()

@cli.command(help='Queue multiple URLs at once.')
@click.option('--path', type=str, required=True, help='Database path.')
@click.option('--file', 'file_', type=str, required=True, help='File with URLs, one URL in each line.')
@click.option('--additional-data', type=str, default=None, show_default=True, help='Additional metadata to associate with the downloaded files.')
@click.option('--metadata-only', type=bool, is_flag=True, default=False, show_default=True, help='Only download metadata.')
@click.option('--overwrite-existing', type=bool, is_flag=True, default=False, show_default=True, help='Overwrite existing files instead of skipping.')
@click.option('--filter', 'filter_', type=str, default=None, show_default=True, help='Filter.')
@click.option('--ignore-anchor', type=bool, is_flag=True, default=False, show_default=True, help='Do not check or update download anchor file.')
@click.option('--max-files', type=int, default=None, show_default=True, help='Maximum number of files to download.')
def mass_add_urls(path: str, file_: str, additional_data: Optional[str], metadata_only: bool, overwrite_existing: bool, filter_: Optional[str], ignore_anchor: bool, max_files: Optional[int]) -> None:
    log.init(path, True)
    db.init(path)
    for line in open(file_, 'r', encoding='utf-8-sig'):
        line = line.strip()
        if line:
            db.add_or_update_urls([{
                'url': line,
                'time_added': time.time(),
                'additional_data': additional_data,
                'metadata_only': metadata_only,
                'overwrite_existing': overwrite_existing,
                'filter': filter_,
                'ignore_anchor': ignore_anchor,
                'max_files': max_files
                }])
            log.info("hydownloader-tools", f"Added URL: {line}")

@cli.command(help='Add multiple subscriptions at once.')
@click.option('--path', type=str, required=True, help='Database path.')
@click.option('--file', 'file_', type=str, required=True, help='File with keywords, one query in each line.')
@click.option('--downloader', type=str, required=True, help='The downloader to use.')
@click.option('--additional-data', type=str, default=None, show_default=True, help='Additional metadata to associate with the downloaded files.')
@click.option('--paused', type=bool, is_flag=True, default=False, show_default=True, help='Set added subscriptions to paused.')
@click.option('--filter', 'filter_', type=str, default=None, show_default=True, help='Filter.')
@click.option('--abort-after', type=int, default=20, show_default=True, help='Abort after this many seen files.')
@click.option('--max-files-initial', type=int, default=None, show_default=True, help='Maximum number of files to download on the first check.')
@click.option('--max-files-regular', type=int, default=None, show_default=True, help='Maximum number of files to download on a regular check.')
@click.option('--check-interval', type=int, required=True, help='Check interval in seconds.')
@click.option('--random-check-interval', type=int, default=0, show_default=True, help='A random number of seconds between 0 and this value will be added to the base check interval.')
@click.option('--encode-keywords', type=bool, is_flag=True, default=False, show_default=True, help="Applies URL encoding to keywords. Spaces are replaced with unencoded '+' characters. Keywords are converted to lowercase.")
@click.option('--skip-existing', type=bool, is_flag=True, default=False, show_default=True, help="Skip adding existing sub queries.")
def mass_add_subscriptions(path: str, file_: str, downloader: str, additional_data: Optional[str], paused: bool, filter_: Optional[str], abort_after: int, max_files_initial: Optional[int], max_files_regular: Optional[int], check_interval: int, random_check_interval: int, encode_keywords: bool, skip_existing: bool) -> None:
    log.init(path, True)
    db.init(path)
    for line in open(file_, 'r', encoding='utf-8-sig'):
        line = line.strip()
        if encode_keywords:
            line = line.replace(' ', '+')
            line = urllib.parse.quote(line, safe='/+').lower()
        if line:
            new_sub = {
                'keywords': line,
                'downloader': downloader,
                'time_created': time.time(),
                'additional_data': additional_data,
                'filter': filter_,
                'paused': paused,
                'check_interval': check_interval + random.randint(0, random_check_interval)
            }
            if max_files_initial is not None:
                new_sub['max_files_initial'] = max_files_initial
            if max_files_regular is not None:
                new_sub['max_files_regular'] = max_files_regular
            if abort_after is not None:
                new_sub['abort_after'] = abort_after
            if skip_existing:
                subs = db.get_subscriptions_by_downloader_data(downloader,line)
                if subs:
                    log.info("hydownloader-tools", f"Skipped existing subscription {line} with downloader {downloader}")
                    continue
            db.add_or_update_subscriptions([new_sub])
            log.info("hydownloader-tools", f"Added subscription {line} with downloader {downloader}")

@cli.command(help='Download Pixiv user profile data for subscribed users (data will be saved to the logs folder).')
@click.option('--path', type=str, required=True, help='Database path.')
@click.option('--cookies', type=str, required=True, help='The cookies.txt file with your Pixiv cookies (to access R18 content).')
@click.option('--user-agent', type=str, required=True, help='User agent (use the same one as the browser you exported the cookies from).')
def download_pixiv_user_profiles(path: str, cookies: str, user_agent: str):
    log.init(path, True)
    db.init(path)

    jar = MozillaCookieJar(cookies)
    jar.load(ignore_discard=True, ignore_expires=True)

    headers = {
        'User-Agent': user_agent
    }

    # check if R18 content is visible, otherwise we will miss a lot of data
    log.info("hydownloader-tools", "Testing access to R18 Pixiv content...")
    test_response = requests.get('https://www.pixiv.net/ajax/user/17282018/profile/all', cookies=jar, headers=headers)
    if test_response.status_code != 200 or not "97831730" in test_response.text:
        log.error("hydownloader-tools", f"Pixiv profile downloader: R18 content is not visible (wrong/missing cookies), aborting")
        log.error("hydownloader-tools", f"Response status: {test_response.status_code}, text: {test_response.text}")
        return
    log.info("hydownloader-tools", "R18 Pixiv content is accessible")

    subs = db.get_subs_by_range()
    pixiv_ids = []
    for sub in subs:
        if sub['downloader'] == 'pixivuser':
            pixiv_ids.append(str(sub['keywords']))

    log.info("hydownloader-tools", f"Found {len(pixiv_ids)} Pixiv user subscriptions. Starting download...")
    counter = 1
    for pid in pixiv_ids:
        log.info("hydownloader-tools", f"Getting profile of Pixiv user {pid} ({counter}/{len(pixiv_ids)})")
        resp = requests.get(f'https://www.pixiv.net/ajax/user/{pid}/profile/all', cookies=jar, headers=headers)
        if resp.status_code != 200:
            log.error("hydownloader-tools", f"Error {resp.status_code} while getting profile for Pixiv user {pid}")
        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        outfile = open(db.get_rootpath()+f"/logs/pixiv-profile-{pid}-{timestamp}.json", "w")
        outfile.write(resp.text)
        outfile.close()
        time.sleep(random.randint(3, 5)+0.12345)
        counter += 1
    log.info("hydownloader-tools", "Finished downloading Pixiv profile data")

@cli.command(help='Force a reparsing of all logfiles.')
@click.option('--path', type=str, required=True, help='Database path.')
def reparse_all_logfiles(path: str) -> None:
    log.init(path, True)
    db.init(path)
    output_postprocessors.parse_log_files(True)

@cli.command(help='List information about available downloaders. Use this command to find out what to write in the "downloader" and "keywords" fields when adding subscriptions.')
def downloaders() -> None:
    print("Downloader".ljust(24)+"URL pattern (will be passed to gallery-dl after filling in {keywords})")
    print("==========".ljust(24)+"======================================================================")
    for downloader in sorted(urls.downloaders.keys()):
        print(downloader.ljust(24)+urls.downloaders[downloader])

def main() -> None:
    if hasattr(signal, 'SIGTTOU'):
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    cli()
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()

if __name__ == "__main__":
    main()
