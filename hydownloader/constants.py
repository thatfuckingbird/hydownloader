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
This file contains the default values of configuration files, SQL commands for creating the hydownloader database and other constants.
These are mostly used when initializing a new hydownloader database.
"""

from typing import Union

API_VERSION = 1

DEFAULT_CONFIG : dict[str, Union[str, int, bool]] = {
    "gallery-dl.executable": "gallery-dl",
    "daemon.port": 53211,
    "daemon.host": "localhost",
    "daemon.ssl": True,
    "daemon.access_key": "change me you retard or get hacked",
    "gallery-dl.archive-override": "",
    "gallery-dl.data-override": "",
    "shared-db-override": ""
}

DEFAULT_IMPORT_JOBS : dict = {
    "default": {
        "apiURL": "http://127.0.0.1:45869",
        "apiKey": "",
        "forceAddMetadata": True,
        "forceAddFiles": False,
        "groups": [
            {"filter": "path.startswith('gallery-dl/pixiv/')",
             "tags": [
                 {
                     "name": "hydl ids",
                     "skipOnError": False,
                     "allowEmpty": False,
                     "tagRepos": ["my tags"],
                     "values": [
                         "['hydl-sub-id:'+s_id for s_id in sub_ids]",
                         "['hydl-url-id:'+u_id for u_id in url_ids]"
                     ]
                 }
             ],
             "urls": [
                 {
                     "name": "artwork url",
                     "skipOnError": False,
                     "allowEmpty": False,
                     "values": "'https://www.pixiv.net/en/artworks/'+str(json_data['id'])"
                 }
             ]
            }
        ]
    }
}

CREATE_SUBS_STATEMENT = """
CREATE TABLE "subscriptions" (
	"id"	INTEGER NOT NULL UNIQUE,
	"keywords"	TEXT NOT NULL,
	"downloader"	TEXT NOT NULL,
	"additional_data"	TEXT,
	"last_check"	INTEGER,
	"check_interval"	INTEGER NOT NULL,
	"priority"	INTEGER NOT NULL DEFAULT 0,
	"paused"	INTEGER NOT NULL DEFAULT 0,
	"time_created"	INTEGER NOT NULL,
	"last_successful_check"	INTEGER,
	"filter"	TEXT,
	"abort_after"	INTEGER NOT NULL DEFAULT 20,
	"max_files_initial"	INTEGER NOT NULL DEFAULT 10000,
	"max_files_regular"	INTEGER,
	"comment"	TEXT,
	PRIMARY KEY("id")
)
"""

CREATE_URL_QUEUE_STATEMENT = """
CREATE TABLE "single_url_queue" (
	"id"	INTEGER NOT NULL UNIQUE,
	"url"	TEXT NOT NULL,
	"priority"	INTEGER NOT NULL DEFAULT 0,
	"ignore_anchor"	INTEGER NOT NULL DEFAULT 0,
	"additional_data"	TEXT,
	"status_text"	TEXT,
	"status"	INTEGER NOT NULL DEFAULT -1,
	"time_added"	INTEGER NOT NULL,
	"time_processed"	INTEGER,
	"metadata_only"	INTEGER NOT NULL DEFAULT 0,
	"overwrite_existing"	INTEGER NOT NULL DEFAULT 0,
	"filter"	TEXT,
	"max_files"	INTEGER,
	"new_files"	INTEGER,
	"already_seen_files"	INTEGER,
	"paused"	INTEGER NOT NULL DEFAULT 0,
	"comment"	TEXT,
	"archived"	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
)
"""

CREATE_ADDITIONAL_DATA_STATEMENT = """
CREATE TABLE "additional_data" (
	"file"	TEXT,
	"subscription_id"	INTEGER,
	"url_id"	INTEGER,
	"data"	INTEGER,
	"time_added"	INTEGER
)
"""

CREATE_VERSION_STATEMENT = """
CREATE TABLE "version" (
	"version"	TEXT NOT NULL UNIQUE
)
"""

CREATE_KNOWN_URLS_STATEMENT = """
CREATE TABLE "known_urls" (
	"url"	TEXT,
	"subscription_id"	INTEGER,
	"url_id"	INTEGER,
	"time_added"	INTEGER,
	"status"	INTEGER DEFAULT 0
)
"""

CREATE_LOG_FILES_TO_PARSE_STATEMENT = """
CREATE TABLE "log_files_to_parse" (
	"file"	TEXT
)
"""

CREATE_SINGLE_URL_INDEX_STATEMENT = """
CREATE INDEX "single_url_index" ON "single_url_queue" (
	"url"
)
"""

CREATE_KEYWORD_INDEX_STATEMENT = """
CREATE INDEX "keyword_index" ON "subscriptions" (
	"keywords"
)
"""

CREATE_KNOWN_URL_INDEX_STATEMENT = """
CREATE INDEX "known_url_index" ON "known_urls" (
	"url"
)
"""

CREATE_SUBSCRIPTION_CHECKS_STATEMENT = """
CREATE TABLE "subscription_checks" (
	"subscription_id"	INTEGER,
	"time_started"	INTEGER,
	"time_finished"	INTEGER,
	"new_files"	INTEGER,
	"already_seen_files"	INTEGER,
	"status"	TEXT,
	"archived"	INTEGER NOT NULL DEFAULT 0
)
"""

SHARED_CREATE_KNOWN_URLS_STATEMENT = """
CREATE TABLE "known_urls" (
	"url"	TEXT,
	"status"	INTEGER NOT NULL
)
"""

SHARED_CREATE_KNOWN_URL_INDEX_STATEMENT = """
CREATE INDEX "known_url_index" ON "known_urls" (
	"url"
)
"""

DEFAULT_GALLERY_DL_USER_CONFIG = R"""{
    "extractor":
    {
        "proxy": null,
        "metadata": true,

        "retries": 4,
        "timeout": 30.0,
        "verify": true,

        "sleep": 3,
        "sleep-request": 1,
        "sleep-extractor": 1,

        "postprocessors": [
            {
                "name": "ugoira",
                "whitelist": ["pixiv", "danbooru"],
                "keep-files": true,
                "ffmpeg-twopass": false,
                "ffmpeg-args": ["-c:v", "libvpx-vp9", "-lossless", "1", "-pix_fmt", "yuv420p", "-y"]
            }
        ],

        "artstation":
        {
            "external": false
        },
        "aryion":
        {
            "username": null,
            "password": null,
            "recursive": true
        },
        "blogger":
        {
            "videos": true
        },
        "danbooru":
        {
            "username": null,
            "password": null,
            "ugoira": false,
            "metadata": true
        },
        "derpibooru":
        {
            "api-key": null,
            "filter": 56027
        },
        "deviantart":
        {
            "extra": true,
            "flat": true,
            "folders": false,
            "include": "gallery",
            "journals": "html",
            "mature": true,
            "metadata": true,
            "original": true,
            "quality": 100,
            "wait-min": 0
        },
        "e621":
        {
            "username": null,
            "password": null
        },
        "exhentai":
        {
            "username": null,
            "password": null,
            "domain": "auto",
            "metadata": false,
            "original": true,
            "sleep-request": 5.0
        },
        "flickr":
        {
            "videos": true,
            "size-max": null
        },
        "furaffinity":
        {
            "descriptions": "text",
            "include": "gallery"
        },
        "gfycat":
        {
            "format": "mp4"
        },
        "hentaifoundry":
        {
            "include": "all"
        },
        "hentainexus":
        {
            "original": true
        },
        "hitomi":
        {
            "metadata": true
        },
        "idolcomplex":
        {
            "username": null,
            "password": null,
            "sleep-request": 5.0
        },
        "imgbb":
        {
            "username": null,
            "password": null
        },
        "imgur":
        {
            "mp4": true
        },
        "inkbunny":
        {
            "username": null,
            "password": null,
            "orderby": "create_datetime"
        },
        "instagram":
        {
            "username": null,
            "password": null,
            "include": "posts",
            "sleep-request": 5.0,
            "videos": true
        },
        "khinsider":
        {
            "format": "mp3"
        },
        "mangadex":
        {
            "api-server": "https://api.mangadex.org"
        },
        "mangoxo":
        {
            "username": null,
            "password": null
        },
        "newgrounds":
        {
            "username": null,
            "password": null,
            "flash": true,
            "include": "art"
        },
        "nijie":
        {
            "username": null,
            "password": null,
            "include": "illustration,doujin"
        },
        "oauth":
        {
            "browser": true,
            "cache": true,
            "port": 6414
        },
        "pillowfort":
        {
            "reblogs": false
        },
        "pinterest":
        {
            "sections": true,
            "videos": true
        },
        "pixiv":
        {
            "avatar": false,
            "tags": "original",
            "ugoira": true
        },
        "reactor":
        {
            "sleep-request": 5.0
        },
        "reddit":
        {
            "comments": 0,
            "morecomments": false,
            "date-min": 0,
            "date-max": 253402210800,
            "date-format": "%Y-%m-%dT%H:%M:%S",
            "id-min": "0",
            "id-max": "zik0zj",
            "recursion": 0,
            "videos": true,
            "user-agent": "Python:gallery-dl:0.8.4 (by /u/mikf1)"
        },
        "redgifs":
        {
            "format": "mp4"
        },
        "sankakucomplex":
        {
            "embeds": false,
            "videos": true
        },
        "sankaku":
        {
            "username": null,
            "password": null
        },
        "smugmug":
        {
            "videos": true
        },
        "seiga":
        {
            "username": null,
            "password": null
        },
        "subscribestar":
        {
            "username": null,
            "password": null
        },
        "tsumino":
        {
            "username": null,
            "password": null
        },
        "tumblr":
        {
            "avatar": false,
            "external": false,
            "inline": true,
            "posts": "all",
            "reblogs": true
        },
        "twitter":
        {
            "username": null,
            "password": null,
            "cards": false,
            "conversations": false,
            "quoted": true,
            "replies": true,
            "retweets": true,
            "twitpic": false,
            "users": "timeline",
            "videos": true
        },
        "unsplash":
        {
            "format": "raw"
        },
        "vsco":
        {
            "videos": true
        },
        "wallhaven":
        {
            "api-key": null
        },
        "weasyl":
        {
            "api-key": null
        },
        "weibo":
        {
            "retweets": true,
            "videos": true
        },
        "booru":
        {
            "tags": true,
            "notes": true
        }
    },

    "downloader":
    {
        "filesize-min": null,
        "filesize-max": null,
        "mtime": true,
        "rate": null,
        "retries": 4,
        "timeout": 30.0,
        "verify": true,

        "http":
        {
            "adjust-extensions": true,
            "headers": null
        },

        "ytdl":
        {
            "format": null,
            "forward-cookies": false,
            "logging": true,
            "module": "youtube_dl",
            "outtmpl": null,
            "raw-options": null
        }
    }
}
"""

DEFAULT_GALLERY_DL_CONFIG = R"""{
    "comment": "DO NOT CHANGE THIS FILE UNLESS YOU KNOW WHAT YOU ARE DOING. IT *WILL* BREAK HYDOWNLOADER.",

    "output": {
        "mode": "pipe",
        "shorten": false,
        "skip": true
    },

    "extractor":
    {
        "cookies-update": true,

        "danbooru": {
            "archive-format": "{id}"
        },

        "gelbooru": {
            "archive-format": "{id}"
        },

        "3dbooru": {
            "archive-format": "{id}"
        },

        "artstation": {
            "archive-format": "{id}"
        },

        "sankakucomplex": {
            "archive-format": "{asset[id]}"
        },

        "pixiv": {
            "archive-format": "{id}{suffix}"
        },

        "twitter": {
            "archive-format": "{tweet_id}_{num}"
        },

        "deviantart": {
            "archive-format": "{index}"
        },

        "patreon": {
            "archive-format": "{id}_{num}"
        },

        "nijie": {
            "archive-format": "{image_id}_{num}"
        },

        "tumblr": {
            "archive-format": "{id}_{num}"
        },

        "webtoons": {
            "archive-format": "{title_no}_{episode}_{num}"
        },

        "kemonoparty": {
            "filename": "{id}_{title}_{filename}_{type[0]}_{num}.{extension}",
            "archive-format": "{service}_{user}_{id}_{filename}_{type[0]}.{extension}"
        },

        "mastodon": {
            "archive-format": "{media[id]}"
        },

        "hentaifoundry": {
            "archive-format": "{index}"
        },

        "moebooru": {
            "archive-format": "{id}"
        }
    }
}
"""
