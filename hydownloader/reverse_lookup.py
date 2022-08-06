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

import os
import shutil
import urllib
import json
import hashlib
import saucenao
from hydownloader import db

def file_md5(filepath: str):
    md5_hash = hashlib.md5()
    with open(filepath,"rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

def run_process(process_list: list[str]):
    process = subprocess.Popen(process_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = process.communicate()
    exit_code = process.wait()
    return output, exit_code

def process_job(job) -> tuple[int, int]: # (status, num. of URLs)
    db.reload_config()
    presets = db.get_conf('reverse-lookup-presets', optional = True)
    if job['config']:
        config = presets[job['config']]
    else:
        config = presets['default']

    job_data_dir = db.get_datapath()+f"/reverse_lookup/job_{job['id']}"
    try:
        os.makedirs(job_data_dir, exist_ok=True)
    except:
        return 1, 0, None

    filepath = None
    if job['file_path']:
        if not os.path.isfile(job['file_path']): return 2, 0, None
        filepath = job['file_path']+'/'+os.path.basename(job['filepath'])
        if not os.path.isfile(filepath):
            try:
                shutil.copy2(job['file_path'], job_data_dir)
            except:
                return 3, 0, None
    elif job['file_url']:
        try:
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if filename:
                filepath = job_data_dir+'/'+filename
            else:
                filepath = job_data_dir+f"/download_revlookup_job_{job['id']}"
        except:
            return 5, 0, None
        if not os.path.isfile(filepath):
            try:
                urllib.urlretrieve(job['file_url'], filepath)
            except:
                return 6, 0, None
    else:
        return 4, 0, None
    filename = os.path.basename(filepath)
    md5 = file_md5(filepath)

    length = 0.0
    probe_output, probe_exit_code = run_process(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath])
    if probe_exit_code != 0:
        pass #TODO show warning, add debug logging everywhere in this function
    else:
        try:
            length = float(probe_output)
        except ValueError:
            pass

    lookup_files = []
    thumb1_filepath = job_data_dir+f"/{job['id']}_thumb1.jpg"
    thumb_exit_code = run_process(['ffmpeg', '-y', '-i', filepath, '-vf', "'scale=320:320:force_original_aspect_ratio=decrease'", '-vframes', '1', thumb1_filepath])[1]
    if thumb_exit_code == 0:
        lookup_files.append(thumb1_filepath)
    else:
        pass # TODO warning
    if length >= 3.0:
        thumb2_filepath = job_data_dir+f"/{job['id']}_thumb2.jpg"
        thumb_exit_code = run_process(['ffmpeg', '-y', '-i', filepath, '-vf', "'thumbnail,scale=320:320:force_original_aspect_ratio=decrease'", '-vframes', '1', thumb2_filepath])[1]
        if thumb_exit_code == 0:
            lookup_files.append(thumb2_filepath)
        else:
            pass # TODO warning
    if not lookup_files:
        lookup_files = [filepath]
        #TODO warning

    additional_results = []
    urls = set()
    for lookup in config['lookups']:
        new_urls_all_files = set()
        for lf in lookup_files:
            if lookup['type'] == 'hashdb':
                pass
            elif lookup['type'] == 'saucenao':
                pass
            elif lookup['type'] == 'iqdb':
                pass
            elif lookup['type'] == 'iqdb3d':
                pass
            elif lookup['type'] == 'filename':
                pass
                break
            elif lookup['type'] == 'ascii2d':
                pass
            elif lookup['type'] == 'exhentai':
                pass
            elif lookup['type'] == 'gelbooru_hash':
                pass
                break
            elif lookup['type'] == 'danbooru_hash':
                pass
                break
            new_urls_all_files = new_urls_all_files | new_urls
        urls = urls | new_urls_all_files
        if new_urls_all_files and lookup.get('stop-on-success', False):
            break

    url_defaults = dict()
    url_dicts = []
    if 'url-defaults' in config:
        url_defaults = config['url-defaults']
    for url in urls:
        url_dict = url_defaults.copy()
        url_dict['paused'] = job['urls_paused']
        url_dict['reverse_lookup_id'] = job['id']
        url_dict['url'] = url
        url_dicts.append(url_dict)
    db.add_or_update_urls(url_dicts)

    return 0, len(urls), json.dumps(additional_results) if additional_results else None

    #do lookups:
    #local hash db
    #hash lookup: gelb,danb + also try to extract hash from filename
    #saucenao
    #exhentai:search for hash (+also try from filename), similarity
    #ascii2d
    #iqdb
    #iqdb3d
    #filename: pixiv,konachan,yandere,lolibooru + try to extract tags
    #example names:
        #https://img3.gelbooru.com//samples/d5/e7/sample_d5e7d513c54d960f45560b1085b4110e.jpg
        #https://konachan.com/jpeg/4193bec48a19bf01a35d6a8e7c64f81c/Konachan.com%20-%20123589%20ass%20bed%20black_hair%20bondage%20breasts%20c:drive%20chain%20fingering%20kotowari%20long_hair%20nipples%20panties%20pussy%20thighhighs%20twintails%20uncensored%20underwear.jpg (1)
    #todo: add an "open url" action to single url queue/rev lookup queue
    #todo: easy way to view all image results
    #todo: work id to artist id database (pixiv)
