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
import saucenao
from hydownloader import db

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
        return 1, 0

    filepath = None
    if job['file_path']:
        if not os.path.isfile(job['file_path']): return 2, 0
        filepath = job['file_path']+'/'+os.path.basename(job['filepath'])
        if not os.path.isfile(filepath):
            try:
                shutil.copy2(job['file_path'], job_data_dir)
            except:
                return 3, 0
    elif job['file_url']:
        try:
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if filename:
                filepath = job_data_dir+'/'+filename
            else:
                filepath = job_data_dir+f"/download_revlookup_job_{job['id']}"
        except:
            return 5, 0
        if not os.path.isfile(filepath):
            try:
                urllib.urlretrieve(job['file_url'], filepath)
            except:
                return 6, 0
    else:
        return 4, 0
    filename = os.path.basename(filepath)

    #download URL if necessary
    #generate images to be looked up:
    #check ffprobe exit code if file is recognized + number of frames https://stackoverflow.com/questions/2017843/fetch-frame-count-with-ffmpeg
    #ffmpeg -ss 00:00:01.00 -i input.mp4 -vf 'scale=320:320:force_original_aspect_ratio=decrease' -vframes 1 output.jpg

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

    # add urls:
    #	"urls_paused"	INTEGER NOT NULL DEFAULT 1,
    #"additional_results"	TEXT,
    #url: set reverse_lookup_id

    #todo: add an "open url" action to single url queue/rev lookup queue
    #todo: work id to artist id database (pixiv)

    return 0, 0
