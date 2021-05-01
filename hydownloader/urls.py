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

import re
from hydownloader import log, uri_normalizer

def subscription_data_to_url(downloader: str, keywords: str) -> str:
    """
    This function takes a hydownloader downloader name (not the same as a gallery-dl downloader name!)
    and some keywords and generates a (usually gallery) URL for gallery-dl to download.
    In Hydrus terms, this does the same thing as a GUG (gallery URL generator).
    """
    if downloader == "gelbooru":
        return f"https://gelbooru.com/index.php?page=post&s=list&tags={keywords}"
    if downloader == "pixivuser":
        return f"https://www.pixiv.net/en/users/{keywords}"
    if downloader == "pixivranking":
        return f"https://www.pixiv.net/ranking.php?mode={keywords}"
    if downloader == "pixivtagsearch":
        return f"https://www.pixiv.net/en/tags/{keywords}/artworks?s_mode=s_tag"
    if downloader == "raw":
        return keywords
    if downloader == "nijieuser":
        return f"https://nijie.info/members.php?id={keywords}"
    if downloader == "lolibooru":
        return f"https://lolibooru.moe/post?tags={keywords}"
    if downloader == "patreon":
        return f"https://www.patreon.com/{keywords}/posts"
    if downloader == "danbooru":
        return f"https://danbooru.donmai.us/posts?tags={keywords}"
    if downloader == "3dbooru":
        return f"http://behoimi.org/post/index?tags={keywords}"
    if downloader == "sankaku":
        return f"https://chan.sankakucomplex.com/?tags={keywords}&commit=Search"
    if downloader == "artstationuser":
        return f"https://www.artstation.com/{keywords}"
    if downloader == "idolcomplex":
        return f"https://idol.sankakucomplex.com/?tags={keywords}&commit=Search"
    if downloader == "twitter":
        return f"https://twitter.com/{keywords}"
    if downloader == "tumblr":
        return f"https://{keywords}.tumblr.com"
    if downloader == "deviantartuser":
        return f"https://deviantart.com/{keywords}"
    if downloader == "fanbox":
        return f"https://{keywords}.fanbox.cc"
    if downloader == "fantia":
        return f"https://fantia.jp/fanclubs/{keywords}"

    log.fatal("hydownloader", f"Invalid downloader: {downloader}")

def subscription_data_from_url(url: str) -> tuple[str, str]:
    """
    This function tries to recognize gallery URLs and generate a hydownloader downloader name and
    some keywords from them to be used as a subscription.
    In Hydrus terms, this is the reverse of what a GUG (gallery URL generator) does.
    """
    u = uri_normalizer.normalizes(url)

    if m := re.match(r"https?://gelbooru\.com/index.php\?page=post&s=list&tags=(?P<keywords>[^&]+)(&.*)?", u):
        return ('gelbooru', m.group('keywords'))
    if m := re.match(r"https?://(www\.)?pixiv\.(net|com)/(en|ja|jp/)?users/(?P<userid>[0-9]+)(/|&.*)?", u):
        return ('pixivuser', m.group('userid'))
    if m := re.match(r"https?://(www\.)?pixiv.(net|com)/member(_illust)?\.php\?id=(?P<userid>[0-9]+)(&.*)?", u):
        return ('pixivuser', m.group('userid'))
    if m := re.match(r"https?://(www\.)?pixiv.(net|com)/ranking\.php\?mode=(?P<mode>[a-z0-9_]+)(&.*)?", u):
        return ('pixivranking', m.group('mode'))
    if m := re.match(r"https?://(www\.)?pixiv.(net|com)/((en|ja|jp)/)?tags/(?P<query>[^/]+)(/.*)?", u):
        return ('pixivtagsearch', m.group('query'))
    if m := re.match(r"https?://nijie\.info/members(_illust)?\.php\?id=(?P<userid>[0-9]+)(&.*)?", u):
        return ('nijieuser', m.group('userid'))
    if m := re.match(r"https?://(www\.)?lolibooru\.moe/post\?tags=(?P<query>[^/]+)(&.*)?", u):
        return ('lolibooru', m.group('query'))
    if m := re.match(r"https?://(www\.)?patreon.com/(?P<username>[^/]+)(/(posts)?)?", u):
        return ('patreon', m.group('username'))
    if m := re.match(r"https?://danbooru\.donmai\.us/posts\?tags=(?P<keywords>[^&]+)(&.*)?", u):
        return ('danbooru', m.group('keywords'))
    if m := re.match(r"https?://(www\.)?behoimi\.org/post/index\?tags=(?P<keywords>[^&]+)(&.*)?", u):
        return ('3dbooru', m.group('keywords'))
    if m := re.match(r"https?://chan\.sankakucomplex\.com/\?tags=(?P<keywords>[^&]+)(&.*)?", u):
        return ('sankaku', m.group('keywords'))
    if (m := re.match(r"https?://(www\.)?artstation\.com/(?P<username>[^/&]+)(&.*)?/?", u)) and not m.group('username') in ['search', 'about', 'subscribe', 'learning', 'marketplace', 'prints', 'jobs', 'blogs', 'contests', 'podcast', 'guides']:
        return ('artstationuser', m.group('username'))
    if m := re.match(r"https?://idol\.sankakucomplex\.com/\?tags=(?P<keywords>[^&]+)(&.*)?", u):
        return ('idolcomplex', m.group('keywords'))
    if m := re.match(r".*(twitter|nitter).*/(?P<username>[^/]+)/status/[0-9]+(&.*)?", u):
        return ('twitter', m.group('username'))
    if m := re.match(r"https?://(www\.)twitter\.com/(?P<username>[^/]+)(/status/[0-9]+(&.*)?)?", u):
        return ('twitter', m.group('username'))
    if (m := re.match(r"https?://(?P<username>[^.]+)\.tumblr\.com.*", u)) and not m.group('username') in ['www', 'download']:
        return ('tumblr', m.group('username'))
    if (m := re.match(r"https?://(?P<username>[^.]+)\.deviantart\.com.*", u)) and not m.group('username') in ['www', 'download']:
        return ('deviantartuser', m.group('username'))
    if m := re.match(r"https?://(www\.)?deviantart\.com/(?P<username>[^/&]+)((&|/).*)?", u):
        return ('deviantartuser', m.group('username'))
    if m := re.match(r"https?://(www\.)?fanbox\.cc/@(?P<username>[^/&]+)((&|/).*)?", u):
        return ('fanbox', m.group('username'))
    if (m := re.match(r"https?://(?P<username>[^.]+)\.fanbox\.cc.*", u)) and not m.group('username') in ['www']:
        return ('fanbox', m.group('username'))
    if m := re.match(r"https?://(www\.)?fantia\.jp/fanclubs/(?P<id>[0-9]+)((&|/).*)?", u):
        return ('fantia', m.group('id'))

    return ('','')

def anchor_patterns_from_url(url: str) -> list[str]:
    """
    This function scans a URL (usually taken from a Hydrus database), and
    generates gallery-dl anchors (in the format that hydownloader uses).
    If multiple anchors can be generated from a single post URL (e.g. it can produce multiple files, like pixiv),
    then this function also generates SQL LIKE-patterns that match all of the anchors belonging to the given post URL.
    The basic, non-LIKE-pattern anchor should always be returned as the first entry in the result list.
    Check the pixiv patterns for an example.

    hydownloader anchor pattern examples for supported sites:
    pixiv: pixiv88847570, pixiv88536044_p00, ..., pixiv88536044_p117
    gelbooru: gelbooru5994487
    danbooru: danbooru4442363
    lolibooru.moe: lolibooru178123
    3dbooru: 3dbooru52352
    artstation: artstation9322141 (difficult, extracted from URL components)
    sankaku: sankaku24860317
    idolcomplex: idolcomplex752647
    twitter: twitter1375563339296768001_1
    deviantart: deviantart873044835
    patreon: patreon48042243_1
    nijie: nijie306993_0, nijie306993_1
    tumblr: tumblr188243485974
    fantia: {post_id}_{file_id}
    fanbox: {id}_{num} (num starts at 1)
    """
    u = uri_normalizer.normalizes(url)

    if m := re.match(r"https?://gelbooru\.com/index\.php\?(page=post&)?(s=view&)?id=(?P<id>[0-9]+)(&.*)?", u):
        return [f"gelbooru{m.group('id')}"]
    if m := re.match(r"https?://(www\.|touch.)?pixiv\.(net|com)/((en|jp|ja)/)?(art)?works/(?P<id>[0-9]+)", u):
        return [f"pixiv{m.group('id')}", f"pixiv{m.group('id')}_%"]
    if m := re.match(r"https?://(www\.|touch.)?pixiv\.(net|com)/member_illust\.php\?illust_id=(?P<id>[0-9]+)(&.*)?", u):
        return [f"pixiv{m.group('id')}", f"pixiv{m.group('id')}_%"]
    if m := re.match(r"https?://(i(mg)?[0-9]+)\.pixiv\.(net|com)/img[0-9]*(/img)?/[^/]+/(?P<id>[0-9]+)((_|\.).*)?", u):
        return [f"pixiv{m.group('id')}", f"pixiv{m.group('id')}_%"]
    if m := re.match(r"https?://(i[0-9]+)\.pixiv\.(net|com)/(img-original|c/1200x1200/img-master)/img/([0-9]+/)+(?P<id>[0-9]+)((_|\.).*)?", u):
        return [f"pixiv{m.group('id')}", f"pixiv{m.group('id')}_%"]
    if m := re.match(r"https?://(www\.|sp.)?nijie\.info/view(_popup)?\.php\?id=(?P<id>[0-9]+)(&.*)?", u):
        return [f"nijie{m.group('id')}", f"nijie{m.group('id')}_%"]
    if m := re.match(r"https?://(www\.)?lolibooru\.moe/post/show/(?P<id>[0-9]+)(&.*)?", u):
        return [f"lolibooru{m.group('id')}"]
    if m := re.match(r"https?://danbooru\.donmai\.us/(posts|post/show|post/view)/(?P<id>[0-9]+)(&.*)?", u):
        return [f"danbooru{m.group('id')}"]
    if m := re.match(r"https?://(www\.)?behoimi\.org/post/show/(?P<id>[0-9]+)(&.*)?", u):
        return [f"3dbooru{m.group('id')}"]
    if m := re.match(r"https?://(beta|chan)\.sankakucomplex\.com/post/show/(?P<id>[0-9]+)(&.*)?", u):
        return [f"sankaku{m.group('id')}"]
    if m := re.match(r"https?://capi-v2\.sankakucomplex\.com/posts\?.*tags=id_range:(?P<id>[0-9]+)(&.*)?", u):
        return [f"sankaku{m.group('id')}"]
    if m := re.match(r"https?://capi-v2\.sankakucomplex\.com/(?P<id>[0-9]+)(&.*)?", u):
        return [f"sankaku{m.group('id')}"]
    if m := re.match(r"https?://idol\.sankakucomplex\.com/post/show/(?P<id>[0-9]+)(&.*)?", u):
        return [f"idolcomplex{m.group('id')}"]
    if m := re.match(r".*\.artstation\.com/.*/images/(?P<raw_id>([0-9]+/)+).*", u):
        id_with_leading_zeroes = "".join(m.group("raw_id").split("/"))
        id_without_leading_zeroes = id_with_leading_zeroes[:]
        while id_without_leading_zeroes.startswith('0'): id_without_leading_zeroes = id_without_leading_zeroes[1:]
        return [f"artstation{id_without_leading_zeroes}", f"artstation{id_with_leading_zeroes}"]
    if m := re.match(r".*(twitter|nitter).*/status(es)?/(?P<id>[0-9]+)(&.*)?", u):
        return [f"twitter{m.group('id')}", f"twitter{m.group('id')}_%"]
    if m := re.match(r"https?://.*\.tumblr.com/post/(?P<id>[0-9]+)(&.*)?", u):
        return [f"tumblr{m.group('id')}", f"tumblr{m.group('id')}_%"]
    if m := re.match(r"https?://(www\.)?deviantart\.com/view/(?P<id>[0-9]+)(&.*)?", u):
        return [f"deviantart{m.group('id')}"]
    if m := re.match(r"https?://.+\.deviantart\.com/([^/]+/)?art/.+-(?P<id>[0-9]+)(&.*)?", u):
        return [f"deviantart{m.group('id')}"]
    if m := re.match(r"https?://.+\.deviantart\.com/download/(P<id>[0-9]+)/.*", u):
        return [f"deviantart{m.group('id')}"]

    return []
