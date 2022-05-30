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
    "shared-db-override": "",
    "disable-wal": False
}

DEFAULT_IMPORT_JOBS = """{
  "default": {
    "apiURL": "http://127.0.0.1:45869",
    "apiKey": "",
    "usePathBasedImport": false,
    "orderFolderContents": "name",
    "nonUrlSourceNamespace": "hydl-non-url-source",
    "groups": [
      {
        "filter": "True",
        "tagReposForNonUrlSources": ["my tags"],
        "metadataOnly": true,
        "tags": [
          {
            "name": "additional tags (with tag repo specified)",
            "allowNoResult": true,
            "values": "[repo+':'+tag for (repo,tag) in get_namespaces_tags(extra_tags, '', None) if repo != '' and repo != 'urls']"
          },
          {
            "name": "additional tags (without tag repo specified)",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "extra_tags[''] if '' in extra_tags else []"
          },
          {
            "name": "hydownloader IDs",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "['hydl-sub-id:'+s_id for s_id in sub_ids]",
              "['hydl-url-id:'+u_id for u_id in url_ids]"
            ]
          },
          {
            "name": "hydownloader source site",
            "tagRepos": [
              "my tags"
            ],
            "values": "'hydl-src-site:'+json_data['category']"
          }
        ],
        "urls": [
          {
            "name": "additional URLs",
            "skipOnError": true,
            "allowNoResult": true,
            "values": "extra_tags['urls']"
          },
          {
            "name": "source URLs from single URL queue",
            "allowNoResult": true,
            "values": "single_urls"
          },
          {
            "name": "gallery-dl file url",
            "values": "json_data.get('gallerydl_file_url', '')",
            "allowEmpty": true
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/pixiv/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "pixiv tags (original), new json format",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "allowTagsEndingWithColon": true,
            "values": "[tag['name'] for tag in json_data['tags']] if not 'untranslated_tags' in json_data else []"
          },
          {
            "name": "pixiv tags (translated), new json format",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "allowTagsEndingWithColon": true,
            "values": "[tag['translated_name'] for tag in json_data['tags'] if tag['translated_name'] is not None] if not 'untranslated_tags' in json_data else []"
          },
          {
            "name": "pixiv tags (original), old json format",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "allowTagsEndingWithColon": true,
            "values": "json_data['untranslated_tags'] if 'untranslated_tags' in json_data else []"
          },
          {
            "name": "pixiv tags (translated), old json format",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "allowTagsEndingWithColon": true,
            "values": "json_data['tags'] if 'untranslated_tags' in json_data else []"
          },
          {
            "name": "pixiv generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'page:'+str(int(json_data['suffix'][2:])+1) if json_data['suffix'] else 'page:1'",
              "'pixiv id:'+str(json_data['id'])",
              "'creator:'+json_data['user']['account']",
              "'creator:'+json_data['user']['name']",
              "'rating:'+json_data['rating']",
              "'pixiv artist id:'+str(json_data['user']['id'])"
            ]
          },
          {
            "name": "pixiv generated tags (title)",
            "allowEmpty": true,
            "allowTagsEndingWithColon": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "('title:'+json_data['title']) if json_data['title'] and json_data['title'].strip() else ''"
            ]
          }
        ],
        "urls": [
          {
            "name": "pixiv artwork url",
            "values": "'https://www.pixiv.net/en/artworks/'+str(json_data['id'])"
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/nijie/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "nijie tags",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "json_data['tags']"
          },
          {
            "name": "nijie generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'title:'+json_data['title']",
              "'page:'+str(json_data['num'])",
              "'nijie id:'+str(json_data['image_id'])",
              "'creator:'+json_data['artist_name']",
              "'nijie artist id:'+str(json_data['artist_id'])"
            ]
          }
        ],
        "urls": [
          {
            "name": "nijie urls",
            "values": [
              "'https://nijie.info/view.php?id='+str(json_data['image_id'])",
              "json_data['url']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/patreon/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "patreon generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'page:'+str(json_data['num'])",
              "'patreon id:'+str(json_data['id'])",
              "'creator:'+json_data['creator']['full_name']",
              "'creator:'+json_data['creator']['vanity']",
              "'patreon artist id:'+str(json_data['creator']['id'])"
            ]
          },
          {
            "name": "patreon generated tags　(title)",
            "allowTagsEndingWithColon": true,
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "('title:'+json_data['title']) if json_data['title'] and json_data['title'].strip() else ''"
            ]
          }
        ],
        "urls": [
          {
            "name": "patreon urls",
            "values": "json_data['url']"
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/newgrounds/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "newgrounds tags",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "json_data['tags']"
          },
          {
            "name": "newgrounds generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'title:'+json_data['title']",
              "'creator:'+json_data['user']",
              "'rating:'+json_data['rating']",
              "('creator:'+artist for artist in json_data['artist'])"
            ]
          }
        ],
        "urls": [
          {
            "name": "newgrounds url",
            "values": [
              "json_data['url']"
            ]
          },
          {
            "name": "newgrounds post url",
            "skipOnError": true,
            "values": [
              "json_data['post_url']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/mastodon/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "mastodon tags",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "json_data['tags']"
          },
          {
            "name": "mastodon generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'mastodon instance:'+json_data['instance']",
              "'mastodon id:'+str(json_data['id'])",
              "'creator:'+json_data['account']['username']",
              "'creator:'+json_data['account']['acct']",
              "'creator:'+json_data['account']['display_name']"
            ]
          }
        ],
        "urls": [
          {
            "name": "mastodon urls",
            "values": [
              "json_data['url']",
              "json_data['uri']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/webtoons/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "webtoons generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'webtoons comic:'+json_data['comic']",
              "'chapter number:'+json_data['episode']",
              "'chapter:'+json_data['title']",
              "'page:'+str(json_data['num'])"
            ]
          }
        ],
        "urls": [
          {
            "name": "webtoons urls",
            "values": "'https://www.webtoons.com/'+json_data['lang']+'/'+json_data['genre']+'/'+json_data['comic']+'/list?title_no='+json_data['title_no']"
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/reddit/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "reddit generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'site:reddit'"
            ]
          }
        ],
        "urls": [
          {
            "name": "reddit urls",
            "values": "'https://i.redd.it/'+json_data['filename']+'.'+json_data['extension']"
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/danbooru/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "danbooru generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'danbooru id:'+str(json_data['id'])",
              "'booru:danbooru'",
              "('pixiv id:'+str(json_data['pixiv_id'])) if json_data['pixiv_id'] else ''"
            ]
          },
          {
            "name": "danbooru tags",
            "allowTagsEndingWithColon": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "[(key+':'+tag if key != 'general' else tag) for (key, tag) in get_namespaces_tags(json_data, 'tag_string_')]"
          }
        ],
        "urls": [
          {
            "name": "danbooru urls",
            "allowEmpty": true,
            "values": [
              "json_data['file_url']",
              "json_data['large_file_url']",
              "json_data['source']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/gelbooru/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "gelbooru generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'gelbooru id:'+str(json_data['id'])",
              "'booru:gelbooru'",
              "'rating:'+json_data['rating']",
              "('title:'+json_data['title']) if json_data['title'] and json_data['title'].strip() else ''"
            ]
          },
          {
            "name": "gelbooru tags",
            "allowTagsEndingWithColon": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "[(key+':'+tag if key != 'general' else tag) for (key, tag) in get_namespaces_tags(json_data, 'tags_')]"
          }
        ],
        "urls": [
          {
            "name": "gelbooru urls",
            "allowEmpty": true,
            "values": [
              "json_data['file_url']",
              "'https://gelbooru.com/index.php?page=post&s=view&id='+str(json_data['id'])",
              "json_data['source']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/sankaku/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "sankaku generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'sankaku id:'+str(json_data['id'])",
              "'booru:sankaku'",
              "'rating:'+json_data['rating']"
            ]
          },
          {
            "name": "sankaku tags",
            "allowTagsEndingWithColon": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "[(key+':'+tag if key != 'general' else tag) for (key, tag) in get_namespaces_tags(json_data, 'tags_', None)]",
              "[(key+':'+tag if key != 'general' else tag) for (key, tag) in get_namespaces_tags(json_data, 'tag_string_')]"
            ]
          }
        ],
        "urls": [
          {
            "name": "sankaku urls",
            "allowEmpty": true,
            "values": [
              "json_data['file_url']",
              "'https://chan.sankakucomplex.com/post/show/'+str(json_data['id'])",
              "json_data['source'] if json_data['source'] else ''"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/idolcomplex/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "idolcomplex generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'idolcomplex id:'+str(json_data['id'])",
              "'booru:idolcomplex'",
              "'rating:'+json_data['rating']"
            ]
          },
          {
            "name": "idolcomplex tags",
            "tagRepos": [
              "my tags"
            ],
            "values": "[(key+':'+tag if key != 'general' else tag) for (key, tag) in get_namespaces_tags(json_data, 'tags_')]"
          }
        ],
        "urls": [
          {
            "name": "idolcomplex urls",
            "allowEmpty": true,
            "values": [
              "json_data['file_url']",
              "'https://idol.sankakucomplex.com/post/show/'+str(json_data['id'])"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/hentaifoundry/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "hentaifoundry generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'title:'+json_data['title']",
              "'medium:'+json_data['media']"
            ]
          },
          {
            "name": "hentaifoundry tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "[tag.replace('_',' ') for tag in json_data['tags']]",
              "json_data['ratings']"
            ]
          }
        ],
        "urls": [
          {
            "name": "hentaifoundry urls",
            "values": [
              "json_data['src']",
              "'https://www.hentai-foundry.com/pictures/user/'+json_data['user']+'/'+str(json_data['index'])"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/deviantart/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "deviantart generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'title:'+json_data['title']",
              "'creator:'+json_data['username']"
            ]
          },
          {
            "name": "deviantart tags",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "json_data['tags']"
          }
        ],
        "urls": [
          {
            "name": "deviantart urls",
            "allowEmpty": true,
            "values": [
              "json_data['content']['src'] if 'content' in json_data else ''",
              "json_data['target']['src'] if 'target' in json_data else ''",
              "json_data['url']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/twitter/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "twitter generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'creator:'+json_data['author']['name']",
              "'creator:'+json_data['author']['nick']",
              "'tweet id:'+str(json_data['tweet_id'])"
            ]
          }
        ],
        "urls": [
          {
            "name": "twitter urls",
            "values": [
              "'https://twitter.com/i/status/'+str(json_data['tweet_id'])",
              "'https://twitter.com/'+json_data['author']['name']+'/status/'+str(json_data['tweet_id'])"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/kemonoparty/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "kemonoparty generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'title:'+json_data['title']",
              "'creator:'+json_data['username']",
              "'kemono.party service:'+json_data['service']",
              "'kemono.party id:'+json_data['id']",
              "'kemono.party user id:'+json_data['user']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/coomerparty/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "coomerparty generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'title:'+json_data['title']",
              "'person:'+json_data['username']",
              "'coomer.party service:'+json_data['service']",
              "'coomer.party id:'+json_data['id']",
              "'coomer.party user id:'+json_data['user']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/directlink/')",
        "tagReposForNonUrlSources": ["my tags"],
        "urls": [
          {
            "name": "directlink url",
            "values": "clean_url('https://'+json_data['domain']+'/'+json_data['path']+'/'+json_data['filename']+'.'+json_data['extension'])"
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/3dbooru/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "3dbooru generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'creator:'+json_data['author']",
              "'booru:3dbooru'",
              "'3dbooru id:'+str(json_data['id'])",
              "'rating:'+json_data['rating']"
            ]
          },
          {
            "name": "3dbooru tags",
            "tagRepos": [
              "my tags"
            ],
            "values": "[(key+':'+tag if key != 'general' else tag) for (key, tag) in get_namespaces_tags(json_data)]"
          }
        ],
        "urls": [
          {
            "name": "3dbooru URLs",
            "values": [
              "json_data['file_url']",
              "'http://behoimi.org/post/show/'+str(json_data['id'])"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/safebooru/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "safebooru generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'safebooru id:'+json_data['id']",
              "'booru:safebooru'",
              "'rating:'+json_data['rating']"
            ]
          },
          {
            "name": "safebooru tags",
            "tagRepos": [
              "my tags"
            ],
            "values": "map(lambda x: x.strip().replace('_', ' '),json_data['tags'].strip().split(' '))"
          }
        ],
        "urls": [
          {
            "name": "safebooru URLs",
            "values": [
              "json_data['file_url']",
              "'https://safebooru.org/index.php?page=post&s=view&id='+json_data['id']",
              "json_data['source']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/tumblr/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "tumblr generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": "'tumblr blog:'+json_data['blog_name']"
          },
          {
            "name": "tumblr tags",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "json_data['tags']"
          }
        ],
        "urls": [
          {
            "name": "tumblr URLs",
            "allowEmpty": true,
            "values": [
              "json_data['short_url']",
              "json_data['post_url']",
              "json_data['photo']['url'] if 'photo' in json_data else ''",
              "json_data['image_permalink'] if 'image_permalink' in json_data else ''"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/fantia/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "fantia generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "('title:'+json_data['content_title'] if 'content_tile' in json_data and json_data['content_title'] else '')",
              "'title:'+json_data['post_title']",
              "'rating:'+json_data['rating']",
              "'fantia user id:'+str(json_data['fanclub_user_id'])",
              "'creator:'+json_data['fanclub_user_name']",
              "'fantia id:'+str(json_data['post_id'])"
            ]
          }
        ],
        "urls": [
          {
            "name": "fantia URLs",
            "values": [
              "json_data['post_url']",
              "json_data['file_url']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/fanbox/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "fanbox generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'creator:'+json_data['creatorId']",
              "'fanbox id:'+json_data['id']",
              "'title:'+json_data['title']",
              "'creator:'+json_data['user']['name']",
              "'fanbox user id:'+json_data['user']['userId']"
            ]
          },
          {
            "name": "fanbox tags",
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "json_data['tags']"
          }
        ],
        "urls": [
          {
            "name": "fanbox URLs",
            "allowEmpty": true,
            "values": [
              "json_data['coverImageUrl'] if json_data['isCoverImage'] else ''",
              "json_data['fileUrl']",
              "'https://'+json_data['creatorId']+'.fanbox.cc/posts/'+json_data['id']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/lolibooru/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "lolibooru generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'lolibooru id:'+str(json_data['id'])",
              "'booru:lolibooru'",
              "'rating:'+json_data['rating']"
            ]
          },
          {
            "name": "lolibooru tags",
            "tagRepos": [
              "my tags"
            ],
            "values": "map(lambda x: x.strip().replace('_', ' '),json_data['tags'].strip().split(' '))"
          }
        ],
        "urls": [
          {
            "name": "lolibooru URLs",
            "allowEmpty": true,
            "values": [
              "json_data['file_url']",
              "'https://lolibooru.moe/post/show/'+str(json_data['id'])",
              "json_data['source']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/yandere/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "yandere generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'yandere id:'+str(json_data['id'])",
              "'booru:yande.re'",
              "'rating:'+json_data['rating']"
            ]
          },
          {
            "name": "yandere tags",
            "tagRepos": [
              "my tags"
            ],
            "values": "map(lambda x: x.strip().replace('_', ' '),json_data['tags'].strip().split(' '))"
          }
        ],
        "urls": [
          {
            "name": "yandere URLs",
            "allowEmpty": true,
            "values": [
              "json_data['file_url']",
              "'https://yande.re/post/show/'+str(json_data['id'])",
              "json_data['source']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/artstation/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "artstation generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'medium:'+json_data['medium']['name'] if json_data['medium'] else ''",
              "['medium:'+med['name'] for med in json_data['mediums']]",
              "['software:'+soft['name'] for soft in json_data['software_items']]",
              "['artstation category:'+cat['name'] for cat in json_data['categories']]",
              "('creator:'+json_data['user']['full_name']) if json_data['user']['full_name'] else ''",
              "'creator:'+json_data['user']['username']",
              "'title:'+json_data['title']"
            ]
          },
          {
            "name": "artstation tags",
            "tagRepos": [
              "my tags"
            ],
            "allowNoResult": true,
            "values": "json_data['tags']"
          }
        ],
        "urls": [
          {
            "name": "artstation asset image URL",
            "skipOnError": true,
            "allowEmpty": true,
            "values": "json_data['asset']['image_url']"
          },
          {
            "name": "artstation permalink",
            "skipOnError": true,
            "allowEmpty": true,
            "values": "json_data['permalink']"
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/imgur/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "imgur album title",
            "tagRepos": [
              "my tags"
            ],
            "skipOnError": true,
            "allowEmpty": true,
            "values": "('title:'+json_data['album']['title']) if json_data['album']['title'] else ''"
          },
          {
            "name": "imgur title",
            "tagRepos": [
              "my tags"
            ],
            "allowEmpty": true,
            "values": "('title:'+json_data['title']) if json_data['title'] and json_data['title'].strip() else ''"
          }
        ],
        "urls": [
          {
            "name": "imgur image URL",
            "values": "json_data['url']"
          },
          {
            "name": "imgur album URL",
            "skipOnError": true,
            "values": "json_data['album']['url']"
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/seisoparty/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "seisoparty generated tags",
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'title:'+json_data['title']",
              "'creator:'+json_data['username']",
              "'seiso.party service:'+json_data['service']",
              "'seiso.party id:'+json_data['id']",
              "'seiso.party user id:'+json_data['user']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/rule34/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "rule34 generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'rule34 id:'+json_data['id']",
              "'booru:rule34'",
              "'rating:'+json_data['rating']"
            ]
          },
          {
            "name": "rule34 tags",
            "allowTagsEndingWithColon": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "[(key+':'+tag if key != 'general' else tag) for (key, tag) in get_namespaces_tags(json_data, 'tags_')]"
          }
        ],
        "urls": [
          {
            "name": "rule34 urls",
            "allowEmpty": true,
            "values": [
              "json_data['file_url']",
              "'https://rule34.xxx/index.php?page=post&s=view&id='+json_data['id']",
              "json_data['source']"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/e621/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "e621 generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'e621 id:' + str(json_data['id'])",
              "'booru:e621'",
              "'rating:' + json_data['rating']"
            ]
          },
          {
            "name": "e621 tags",
            "allowTagsEndingWithColon": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "get_nested_tags_e621(json_data['tags'])"
          },
          {
            "name": "e621 post tags",
            "allowTagsEndingWithColon": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "get_nested_tags_e621(json_data['tags'])"
          }
        ],
        "urls": [
          {
            "name": "e621 urls",
            "allowEmpty": true,
            "values": [
              "json_data['gallerydl_file_url']",
              "'https://e621.net/posts/' + str(json_data['id'])"
            ]
          }
        ]
      },
      {
        "filter": "pstartswith(path, 'gallery-dl/furaffinity/')",
        "tagReposForNonUrlSources": ["my tags"],
        "tags": [
          {
            "name": "furaffinity generated tags",
            "allowEmpty": true,
            "tagRepos": [
              "my tags"
            ],
            "values": [
              "'furaffinity id:'+str(json_data['id'])",
              "'booru:furaffinity'",
              "'rating:'+json_data['rating']",
              "'creator:'+json_data['artist']",
              "'title:'+json_data['title']",
              "('gender:'+json_data['gender']) if json_data['gender'] != 'Any' else ''",
              "('species:'+json_data['species']) if json_data['species'] != 'Unspecified / Any' else ''"
            ]
          },
          {
            "name": "furaffinity tags",
            "allowTagsEndingWithColon": true,
            "allowEmpty": true,
            "allowNoResult": true,
            "tagRepos": [
              "my tags"
            ],
            "values": "[tag.replace('_', ' ') for tag in json_data['tags']]"
          }
        ],
        "urls": [
          {
            "name": "furaffinity urls",
            "allowEmpty": true,
            "values": [
              "json_data['url']",
              "'https://www.furaffinity.net/view/'+str(json_data['id'])+'/'"
            ]
          }
        ]
      }
    ]
  }
}
"""

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
	"gallerydl_config"	TEXT,
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
	"gallerydl_config"	TEXT,
	"max_files"	INTEGER,
	"new_files"	INTEGER,
	"already_seen_files"	INTEGER,
	"paused"	INTEGER NOT NULL DEFAULT 0,
	"comment"	TEXT,
	"reverse_lookup_id"	INTEGER,
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
	"file"	TEXT,
	"worker"	TEXT NOT NULL
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

CREATE_MISSED_SUBSCRIPTION_CHECKS_STATEMENT = """
CREATE TABLE "missed_subscription_checks" (
	"subscription_id"	INTEGER,
	"time"	INTEGER,
	"reason"	INTEGER,
	"data"	TEXT,
	"archived"	INTEGER NOT NULL DEFAULT 0
)
"""

CREATE_URL_ID_INDEX_STATEMENT = """
CREATE INDEX "url_id_index" ON "additional_data" (
	"url_id"
)
"""

CREATE_SUBSCRIPTION_ID_INDEX_STATEMENT = """
CREATE INDEX "subscription_id_index" ON "additional_data" (
	"subscription_id"
)
"""

CREATE_FILE_INDEX_STATEMENT = """
CREATE INDEX "file_index" ON "additional_data" (
	"file"
)
"""

CREATE_REVERSE_LOOKUP_JOBS_STATEMENT = """
CREATE TABLE "reverse_lookup_jobs" (
	"id"	INTEGER NOT NULL UNIQUE,
	"file_path"	TEXT,
	"file_url"	TEXT,
	"config"	TEXT NOT NULL,
	"status"	INTEGER NOT NULL,
	"time_added"	INTEGER NOT NULL,
	"paused"	INTEGER NOT NULL DEFAULT 0,
	"urls_paused"	INTEGER NOT NULL DEFAULT 1,
	"priority"	INTEGER NOT NULL DEFAULT 0,
	"result_count"	INTEGER,
	"time_processed"	INTEGER,
	"additional_results"	TEXT,
	PRIMARY KEY("id")
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

SHARED_CREATE_IMPORTED_FILES_STATEMENT = """
CREATE TABLE "imported_files" (
	"filename"	TEXT NOT NULL,
	"import_time"	INTEGER NOT NULL,
	"creation_time"	INTEGER NOT NULL,
	"modification_time"	INTEGER NOT NULL,
	"metadata"	BLOB,
	"hash"	TEXT NOT NULL
)
"""

SHARED_CREATE_IMPORTED_FILE_INDEX_STATEMENT = """
CREATE INDEX "imported_file_index" ON "imported_files" (
	"filename"
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
                "ffmpeg-args": ["-nostdin", "-c:v", "libvpx-vp9", "-lossless", "1", "-pix_fmt", "yuv420p", "-y"]
            }
        ],

        "tags": true,
        "external": true,
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
            "ugoira": true,
            "metadata": true,
            "include": "artworks",
            "ranking": {
                "max-posts": 100
            }
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
            "videos": true,
            "fallback": false
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
        },
        "moebooru":
        {
            "tags": true,
            "notes": true
        },
        "kemonoparty":
        {
            "metadata": true,
            "comments": true,
            "dms": true,
            "duplicates": true
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

    "url-metadata": "gallerydl_file_url",
    "signals-ignore": ["SIGTTOU", "SIGTTIN"],

    "output": {
        "mode": "pipe",
        "shorten": false,
        "skip": true
    },

    "downloader":
    {
        "progress": null,

        "ytdl": {
            "module": "yt_dlp"
        }
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

        "sankaku": {
            "archive-format": "{id}"
        },

        "pixiv": {
            "archive-format": "{id}{suffix}"
        },

        "twitter": {
            "archive-format": "{tweet_id}_{num}",
            "image": {
              "archive-format": "image{filename}"
            },
            "syndication": true
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
            "filename": "{id}_{hash}_{type[0]}_{num}.{extension}",
            "archive-format": "{service}_{user}_{id}_{filename}_{type[0]}.{extension}"
        },

        "coomerparty": {
            "filename": "{id}_{hash}_{type[0]}_{num}.{extension}",
            "archive-format": "{service}_{user}_{id}_{filename}_{type[0]}.{extension}"
        },

        "mastodon": {
            "archive-format": "{id}_{media[id]}"
        },

        "hentaifoundry": {
            "archive-format": "{index}"
        },

        "moebooru": {
            "archive-format": "{id}"
        },

        "ytdl": {
            "module": "yt_dlp"
        },

        "rule34": {
            "archive-format": "{id}"
        },

        "e621": {
            "archive-format": "{id}"
        },

        "furaffinity": {
            "external": false,
            "filename": "{id}.{extension}",
            "archive-format": "{id}"
        }
    }
}
"""
