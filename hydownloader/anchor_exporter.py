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

import sqlite3
import os
import sys
import collections
from typing import Optional, Counter, Tuple
import click
from hydownloader import db, log, urls

@click.group()
def cli() -> None:
    pass

@cli.command(help='Add entries to an anchor database based on the URLs stored in a Hydrus database.')
@click.option('--path', type=str, required=True, help='hydownloader database path.')
@click.option('--hydrus-db-folder', type=str, required=True, help='Hydrus database directory (where the .db files are located).')
@click.option('--sites', type=str, required=True, default='all', help='A comma-separated list of sites to add anchor entries for. Currently supported: pixiv, gelbooru, nijie, lolibooru, danbooru, 3dbooru, sankaku, idolcomplex, artstation, twitter, deviantart, tumblr, hentaifoundry. The special \'all\' value can be used to mean all supported sites (this is the default).')
@click.option('--unrecognized-urls-file', type=str, required=False, default=None, help="Write URLs that are not recognized by the anchor generator but could be related to the listed sites into a separate file. You can check this file to see if there are any URLs that should have been used for generating anchors but weren't.")
@click.option('--recognized-urls-file', type=str, required=False, default=None, help="Write URLs that were recognized by the anchor generator to this file.")
@click.option('--fill-known-urls', type=bool, is_flag=True, required=False, default=False, help="Transfer all Hydrus URLs into the hydownloader database as known URLs.")
@click.option('--keep-old-hydrus-url-data', type=bool, is_flag=True, required=False, default=False, help="If this is true when --fill-known-urls is used, then old URL data exported from Hydrus in previous runs of this tool will be kept in the hydownloader known URL database. This is useful only if you want to export URLs from multiple Hydrus databases, in which case you should set this to true when calling this tool with the 2nd and later databases. In other cases enabling this will lead to outdated and/or duplicated data.")
def update_anchor(path: str, hydrus_db_folder: str, sites: str, unrecognized_urls_file: Optional[str], recognized_urls_file: Optional[str], fill_known_urls: bool, keep_old_hydrus_url_data: bool) -> None:
    """
    This function goes through all URLs in a Hydrus database, and tries to match them to known site-specific URL patterns to
    generate anchor database entries that gallery-dl can recognize. For some sites, the anchor format differs
    from the gallery-dl default, these are set in gallery-dl-config.json.
    If enabled, also fills up the known_urls table in the hydownloader DB with all URLs known by Hydrus.
    """
    log.init(path, True)
    db.init(path)
    if not os.path.isfile(hydrus_db_folder+"/client.master.db"):
        log.fatal("hydownloader-anchor-exporter", "The client.master.db database was not found at the given location!")
    hydrus_db = sqlite3.connect(hydrus_db_folder+"/client.master.db")
    hydrus_db.row_factory = sqlite3.Row
    anchor_init_needed = not os.path.isfile(path+"/anchor.db")
    anchor_db = sqlite3.connect(path+"/anchor.db")
    hc = hydrus_db.cursor()
    ac = anchor_db.cursor()
    if anchor_init_needed:
        ac.execute('CREATE TABLE archive (entry PRIMARY KEY) WITHOUT ROWID')
        anchor_db.commit()
    ac.execute('select * from archive')
    known_anchors = {row[0] for row in ac.fetchall()}
    log.info("hydownloader-anchor-exporter", "Querying Hydrus database for URLs...")
    hc.execute('select * from url_domains natural inner join urls')
    rows = hc.fetchall()
    all_rows = len(rows)
    processed = 0
    suspicious_urls = set()
    recognized_urls = set()
    current_url_ids = set()
    deleted_url_ids = set()
    if fill_known_urls:
        if not os.path.isfile(hydrus_db_folder+"/client.db"):
            log.fatal("hydownloader-anchor-exporter", "The client.db database was not found at the given location!")
        client_db = sqlite3.connect(hydrus_db_folder+"/client.db")
        client_db.row_factory = sqlite3.Row
        cc = client_db.cursor()
        log.info("hydownloader-anchor-exporter", "Querying Hydrus database for current URL IDs...")
        cc.execute('select * from current_files natural inner join url_map')
        for row in cc.fetchall():
            current_url_ids.add(row['url_id'])
        log.info("hydownloader-anchor-exporter", "Querying Hydrus database for deleted URL IDs...")
        cc.execute('select * from deleted_files natural inner join url_map')
        for row in cc.fetchall():
            deleted_url_ids.add(row['url_id'])
        client_db.close()
        if keep_old_hydrus_url_data:
            log.info("hydownloader-anchor-exporter", "Old Hydrus URL data will NOT be deleted from the shared hydownloader database")
        else:
            log.info("hydownloader-anchor-exporter", "Deleting old Hydrus URL data from shared hydownloader database...")
            db.delete_all_hydrus_known_urls()

    sites_to_keywords : dict[str, Tuple[list[str], list[str]]] = {
        'pixiv': (["pixi"],[]),
        'gelbooru': (["gelbooru"],[]),
        'nijie': (["nijie"],[]),
        'lolibooru': (['lolibooru'],[]),
        'danbooru': (['danbooru'],[]),
        '3dbooru': (['behoimi'],[]),
        'sankaku': (['sankaku'],["idol."]),
        'idolcomplex': (["idol.sankaku"],[]),
        'artstation': (["artstation"],[]),
        'twitter': (["twitter", "nitter"],[]),
        'deviantart': (['deviantart'],[]),
        'tumblr': (["tumblr"],[]),
        'hentaifoundry': (["hentai-foundry"],[])
    }

    siteset = {x.strip() for x in sites.split(',') if x.strip()}
    if sites == "all":
        siteset = set(sites_to_keywords.keys())
    anchors : Counter[str] = collections.Counter()

    for site in siteset:
        if not site in sites_to_keywords:
            log.fatal('hydownloader-anchor-exporter', f'Unsupported site: {site}')

    def process_url(url):
        patterns = urls.anchor_patterns_from_url(url)
        if patterns:
            recognized_urls.add(url)
            anchors[patterns[0]] += 1
        else:
            suspicious_urls.add(url)

    log.info("hydownloader-anchor-exporter", "Processing URLs...")
    for row in rows:
        processed += 1
        if processed % 1000 == 0:
            print(f"Processed {processed}/{all_rows} URLs", file=sys.stderr)
        if fill_known_urls:
            known_url_status = 1
            is_current = row['url_id'] in current_url_ids
            is_deleted = row['url_id'] in deleted_url_ids
            if is_current and is_deleted:
                known_url_status = 4
            elif is_deleted:
                known_url_status = 3
            elif is_current:
                known_url_status = 2
            db.add_hydrus_known_url(row['url'], known_url_status)
        for site in siteset:
            accepts, rejects = sites_to_keywords[site]
            url_ok = False
            for accept in accepts:
                if accept in row['url']:
                    url_ok = True
                    break
            if url_ok:
                for reject in rejects:
                    if reject in row['url']: url_ok = False
            if url_ok:
                process_url(row['url'])
    log.info("hydownloader-anchor-exporter", "Done processing URLs")

    if unrecognized_urls_file:
        log.info("hydownloader-anchor-exporter", "Writing unrecognized URLs...")
        with open(unrecognized_urls_file, 'w', encoding='utf-8-sig') as f:
            for url in sorted(suspicious_urls):
                f.write(url.strip()+'\n')
        log.info("hydownloader-anchor-exporter", "Done writing unrecognized URLs")
    if recognized_urls_file:
        log.info("hydownloader-anchor-exporter", "Writing recognized URLs...")
        with open(recognized_urls_file, 'w', encoding='utf-8-sig') as f:
            for url in sorted(recognized_urls):
                f.write(url.strip()+'\n')
        log.info("hydownloader-anchor-exporter", "Done writing recognized URLs")

    log.info("hydownloader-anchor-exporter", "Inserting new anchors...")
    anchor_count = len(anchors.keys())
    processed = 0
    new_anchor_rows = 0
    for anchor in anchors:
        processed += 1
        if processed % 50 == 0:
            print(f"Inserting new anchors {processed}/{anchor_count}", file=sys.stderr)
        final_anchors = [anchor]
        if anchor.startswith("nijie"):
            for i in range(anchors[anchor]):
                final_anchors.append(anchor+"_"+str(i))
        if anchor.startswith("twitter") or anchor.startswith("tumblr"):
            for i in range(anchors[anchor]+1):
                final_anchors.append(anchor+"_"+str(i))
        if anchor.startswith("pixiv"):
            for i in range(anchors[anchor]):
                final_anchors.append(anchor+"_p{:02d}".format(i))
        for f_a in final_anchors:
            if f_a in known_anchors:
                continue
            ac.execute('insert into archive(entry) values (?)', (f_a,))
            new_anchor_rows += 1
    log.info("hydownloader-anchor-exporter", f"Done inserting new anchors, added {new_anchor_rows} entries in total")

    anchor_db.commit()
    anchor_db.close()
    hydrus_db.close()
    db.shutdown()

def main() -> None:
    cli()
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()

if __name__ == "__main__":
    main()
