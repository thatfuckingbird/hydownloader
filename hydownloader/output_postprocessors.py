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

import os
import re
import glob
from typing import Optional
from hydownloader import db, log

def process_additional_data(subscription_id: Optional[int] = None, url_id: Optional[int] = None) -> tuple[int, int]:
    """
    This function scans log files outputted by gallery-dl and tries to recognize filenames in the output.
    Based on which subscription or URL those files belong to, it queries the database for the associated additional_data
    values (from the subscriptions or single_url_queue tables), then inserts these filename + data entries
    into the additional_data database table (even if there is no additional_date for the given files).
    This way it is possible to keep track which files were found by which URL downloads/subscriptions, and correctly
    associate additional data with them (even if the files were not actually downloaded by the URL or sub because
    some earlier download already got them).
    If both the subscription and url ID arguments are None, then it scans all files in the temp directory, otherwise
    exactly one of those must not be None and then it only scans for the file belonging to that URL or subscription.
    When parsing gallery-dl output, it is much better to have false positives (recognize some output lines as filenames which are not)
    than to miss any actual filenames, since invalid filename entries in the additional_data table are not a big deal.
    """
    def is_filepath(candidate: str) -> bool:
        candidate = candidate.strip()
        # return ("/" in candidate or "\\" in candidate) and not candidate.startswith("[") and not "gallery-dl:" in candidate
        return os.path.exists(candidate)
    skipped_count = 0
    new_count = 0
    if subscription_id is not None and os.path.isfile(db.get_rootpath()+f"/temp/subscription-{subscription_id}-gallery-dl-output.txt"):
        f = open(db.get_rootpath()+f"/temp/subscription-{subscription_id}-gallery-dl-output.txt", 'r')
        for line in f:
            line = line.strip()
            if not is_filepath(line):
                log.debug("hydownloader", f"Does not look like a filepath: {line}")
                continue
            if line.startswith("# "):
                log.debug("hydownloader", f"Looks like a skipped filepath: {line}")
                line = line[1:]
                line = line.strip()
                skipped_count += 1
            else:
                log.debug("hydownloader", f"Looks like a new filepath: {line}")
                new_count += 1
            db.associate_additional_data(filename=line, subscription_id=subscription_id)
        f.close()
        os.remove(db.get_rootpath()+f"/temp/subscription-{subscription_id}-gallery-dl-output.txt")
    elif url_id is not None and os.path.isfile(db.get_rootpath()+f"/temp/single-url-{url_id}-gallery-dl-output.txt"):
        f = open(db.get_rootpath()+f"/temp/single-url-{url_id}-gallery-dl-output.txt", 'r')
        for line in f:
            line = line.strip()
            if not is_filepath(line):
                log.debug("hydownloader", f"Does not look like a filepath: {line}")
                continue
            if line.startswith("# "):
                log.debug("hydownloader", f"Looks like a skipped filepath: {line}")
                line = line[1:]
                line = line.strip()
                skipped_count += 1
            else:
                log.debug("hydownloader", f"Looks like a new filepath: {line}")
                new_count += 1
            db.associate_additional_data(filename=line, url_id=url_id)
        f.close()
        os.remove(db.get_rootpath()+f"/temp/single-url-{url_id}-gallery-dl-output.txt")
    else:
        log.info("hydownloader", "Checking for any leftover temporary gallery-dl output files...")
        filenames = os.listdir(db.get_rootpath()+"/temp")
        for filename in filenames:
            if match := re.match("single-url-([0-9]+)-gallery-dl-output.txt", filename.strip()):
                log.info("hydownloader", f"Processing leftover file {filename}...")
                process_additional_data(url_id = int(match.group(1)))
            elif match := re.match("subscription-([0-9]+)-gallery-dl-output.txt", filename.strip()):
                log.info("hydownloader", f"Processing leftover file {filename}...")
                process_additional_data(subscription_id = int(match.group(1)))
    return new_count, skipped_count

def parse_log_files(all_files: bool = False):
    if all_files:
        logs = glob.glob(db.get_rootpath()+"/logs/single-urls-*-gallery-dl-*.txt") + glob.glob(db.get_rootpath()+"/logs/subscription-*-gallery-dl-*.txt")
        for l in logs:
            db.add_log_file_to_parse_queue(l)
    while logfname := db.get_queued_log_file():
        subscription_id = None
        url_id = None
        if m := re.match(r".*(?:\\|\/)single-urls-([0-9]+)-gallery-dl-.*\.txt", logfname):
            url_id = int(m.group(1))
        if m := re.match(r".*(?:\\|\/)subscription-([0-9]+)-gallery-dl-.*\.txt", logfname):
            subscription_id = int(m.group(1))
        with open(db.get_rootpath()+"/"+logfname, 'r') as logf:
            log.info("hydownloader", f"Parsing log file: {logfname}")
            urls = []
            for line in logf:
                if m := re.match(r'\[urllib3\.connectionpool\]\[debug\] (http.*?)(?::[0-9]+)? "[A-Z]+ (\/.*?) HTTP.*', line.strip()):
                    urls.append(m.group(1)+m.group(2))
                if m := re.match(r".*Starting DownloadJob for '(.*)'$", line.strip()):
                    urls.append(m.group(1))
            db.add_known_urls(urls, subscription_id = subscription_id, url_id = url_id)
            db.remove_log_file_from_parse_queue(db.get_rootpath()+"/"+logfname)
            log.info("hydownloader", f"Finished parsing log file {logfname}, found {len(urls)} URLs")
