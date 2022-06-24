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

import json
import os
import os.path
import sys
import io
import re
import time
import itertools
import hashlib
import urllib.parse
import requests
import urllib3.util.retry
from collections import defaultdict
from typing import Optional, Union, Any
import click
import hydrus_api
import dateutil.parser
from hydownloader import db, log

def unfuck_path_separator(path: str) -> str:
    if os.name == 'nt':
        return path.replace('\\', '/')
    return path

def get_session(retries: Union[int, float], backoff_factor=Union[int, float]) -> requests.Session:
    session = requests.session()
    # https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/#combining-timeouts-and-retries
    retry = urllib3.util.retry.Retry(
        total=retries,
        backoff_factor=backoff_factor
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Helper function to use in user-defined importer expressions
def get_namespaces_tags(data: dict[str, Any], key_prefix : str = 'tags_', separator : Optional[str] =' ') -> list[tuple[str,str]]:
    prefix_length = len(key_prefix)
    def split_val(val):
        if separator:
            return map(lambda x: x.replace('_', ' '), val.split(separator))
        else:
            return map(lambda x: x.replace('_', ' '), val)
    pairs = list(itertools.chain.from_iterable(map(lambda x: itertools.product((x[0][prefix_length:],),split_val(x[1])), filter(lambda x: x[0].startswith(key_prefix), data.items()))))
    final_result = []
    for pair in pairs:
        if not pair[1]: continue
        if pair[0] == 'artist':
            final_result.append(('creator',pair[1]))
        elif pair[0] == 'copyright':
            final_result.append(('series',pair[1]))
        else:
            final_result.append(pair)
    return final_result

# Get tags from a nested JSON entry
# Example from 3621
# {
#     "tags": {
#         "artist": [
#             "artist_name"
#         ],
#         "character": [],
#         "general": [
#             "furry",
#             "gay_furry",
#             "straight_furry"
#         ]
#     }
# }
# data should be the tags entry like "json_data['tags']
def get_nested_tags_e621(data: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for namespace in data.items():
        ns = namespace[0]
        if ns == 'invalid':
            #  e621 replaces tags they don't want with this or something like that, weird
            pass
        elif ns == 'general':
            ns = ''
        elif ns == 'artist':
            ns = 'creator'
        elif ns == 'copyright':
            ns = 'series'

        if ns != '':
            ns = ns + ":"

        for tag in namespace[1]:
            tags.append(ns + tag.replace("_", " "))

    return tags

# Helper function to use in user-defined importer expressions
def clean_url(url: str) -> str:
    return re.sub(r'(?<!:)//', '/', url)

def is_valid_url(url: str) -> bool:
    try:
        result = urllib.parse.urlsplit(url.strip())
        return bool(result.netloc and result.scheme)
    except ValueError:
        return False

def convdate(date: str) -> str:
    return dateutil.parser.parse(date).strftime("%Y-%m-%d")

def convtime(time: str) -> str:
    return dateutil.parser.parse(time).strftime("%H:%M:%S")

def convdatetime(datetime: str) -> str:
    return dateutil.parser.parse(datetime).strftime("%Y-%m-%d %H:%M:%S")

def skip_file(fname: str) -> bool:
    # json files hold metadata, don't import them to Hydrus
    if fname.endswith('.json'):
        return True

    # skip files still being downloaded
    if fname.endswith('.part'):
        return True

    # already imported file
    if fname.endswith('.HYDL-IMPORTED'):
        return True

    # Skip windows 'Thumbs.db` file
    if fname == 'Thumbs.db':
        return True

    return False

@click.group()
def cli() -> None:
    pass

def printerr(msg: Union[str, Exception], quit: bool) -> None:
    print(msg, file=sys.stderr)
    if quit:
        db.sync()
        sys.exit(1)

def pstartswith(path1: str, path2: str) -> bool:
    return path1.startswith(path2) or unfuck_path_separator(path1).startswith(unfuck_path_separator(path2))

def parse_additional_data(result: defaultdict[str, list[str]], data_str: str) -> None:
    """
    This parses the data field of the additonal_data table.
    Currently there are 3 supported formats:
        * empty
        * comma-separated list of tags
        * JSON-object generated by Hydrus Companion,
          format according to the Hydrus API /add_urls/add_url endpoint input format
    """
    if not data_str:
        return
    simple_string = True
    if data_str.strip().startswith('{'):
        d = {}
        try:
            d = json.loads(data_str)
            simple_string = False
        except json.decoder.JSONDecodeError:
            pass
        if "url" in d:
            result["urls"].append(str(d.get("url")))
        s_to_t = d.get("service_names_to_tags", {})
        for key in s_to_t:
            result[key].extend(s_to_t[key])
    if simple_string:
        result[""].extend(x.strip() for x in data_str.split(',') if x.strip())

@cli.command(help='List, rename or delete already imported files')
@click.option('--path', type=str, required=True, help='hydownloader database path.')
@click.option('--action', type=str, required=True, help='The action to perform. One of list, rename, delete.')
@click.option('--do-it', type=bool, is_flag=True, default=False, show_default=True, help='Actually do the renaming or deleting. Off by default.')
@click.option('--no-skip-on-differing-times', type=bool, is_flag=True, default=False, show_default=True, help='Do not skip files that have different creation or modification date than what is in the database of already imported files.')
@click.option('--no-include-metadata', type=bool, is_flag=True, default=False, show_default=True, help='Do not include metadata files in the action.')
def clear_imported(path: str, action: str, do_it: bool, no_skip_on_differing_times: bool, no_include_metadata: bool):
    if action not in ["list", "rename", "delete"]:
        log.fatal("hydownloader-importer", f"Invalid action: {action}")

    log.init(path, True)
    db.init(path)

    log.info("hydownloader-importer", f"Collecting files for action: {action}")

    collected_files : list[tuple[str, str]] = []

    data_path = db.get_datapath()
    for root, _, files in os.walk(data_path):
        for fname in files:
            if skip_file(fname):
                continue

            abspath = root + "/" + fname
            path = os.path.relpath(abspath, start = data_path)
            ctime = os.stat(abspath).st_ctime
            mtime = os.stat(abspath).st_mtime

            is_file_in_import_db, db_mtime, db_ctime = db.check_import_db(path)
            if not is_file_in_import_db: continue

            if ctime != db_ctime or mtime != db_mtime:
                if not no_skip_on_differing_times:
                    continue

            # find the path of the associated json metadata file, check if it exists
            # for pixiv ugoira, the same metadata file belongs both to the .webm and the .zip,
            # so this needs special handling
            json_path = abspath+'.json'
            if not os.path.isfile(json_path) and abspath.endswith('.webm'):
                json_path = abspath[:-4]+"zip.json"
            json_exists = os.path.isfile(json_path)
            json_relpath = os.path.relpath(json_path, start = data_path)

            collected_files.append((path,abspath))
            if json_exists and not no_include_metadata:
                collected_files.append((json_relpath,json_path))

    log.info("hydownloader-importer", f"Executing action: {action}")
    for relpath, abspath in collected_files:
        if action == "list":
            print(relpath)
        elif action == "delete":
            print(f"Deleting {abspath}")
            if do_it: os.remove(abspath)
        elif action == "rename":
            print(f"Renaming {abspath}")
            if do_it: os.rename(abspath, abspath+".HYDL-IMPORTED")

@cli.command(help='Run an import job to transfer files and metadata into Hydrus.')
@click.option('--path', type=str, required=True, help='hydownloader database path.')
@click.option('--job', type=str, required=True, help='Name of the import job to run.')
@click.option('--skip-already-imported', type=bool, required=False, default=False, is_flag=True, show_default=True, help='Skip files that were already imported in the past (based on hydownloader\'s database of imported files).')
@click.option('--no-skip-on-differing-times', type=bool, required=False, default=False, is_flag=True, show_default=True, help='Do not skip files that have different creation or modification date than what is in the database of already imported files. This flag only has effect when --skip-already-imported is used.')
@click.option('--config', type=str, required=False, default=None, show_default=True, help='Import job configuration filepath override.')
@click.option('--verbose', type=bool, is_flag=True, default=False, show_default=True, help='Print generated metadata and other information.')
@click.option('--do-it', type=bool, is_flag=True, default=False, show_default=True, help='Actually do the importing. Off by default.')
@click.option('--no-abort-on-missing-metadata', type=bool, is_flag=True, show_default=True, default=False, help='Do not stop importing when a metadata file is not found.')
@click.option('--filename-regex', type=str, default=None, show_default=True, help='Only run the importer on files whose filepath matches the regex given here. This is an additional restriction on top of the filters defined in the import job.')
@click.option('--no-abort-on-error', type=bool, default=False, show_default=True, is_flag=True, help='Do not abort on errors. Useful to check for any potential errors before actually importing files.')
@click.option('--no-abort-when-truncated', type=bool, default=False, show_default=True, is_flag=True, help='Do not abort when a file is truncated. Subset of errors covered wtih \'--no-abort-on-error\'')
@click.option('--no-abort-on-hydrus-import-failure', type=bool, default=False, show_default=True, is_flag=True, help='Do not abort when hydrus fails to import a file due to corruption, truncation, or being veto\'d. Subset of errors covered wtih \'--no-abort-on-error\'')
@click.option('--no-force-add-metadata', type=bool, default=False, show_default=True, is_flag=True, help='Do not add metadata for files already in Hydrus.')
@click.option('--force-add-files', type=bool, default=False, show_default=True, is_flag=True, help='Send files to Hydrus even if they are already in Hydrus.')
@click.option('--subdir', type=str, default=None, show_default=True, help='Only scan a subdirectory within the database\'s \'gallery-dl\' folder to target specific files, e.g. \'gelbooru/tag\' to import a specific gelbooru tag.')
def run_job(path: str, job: str, skip_already_imported: bool, no_skip_on_differing_times: bool, config: Optional[str], verbose: bool, do_it: bool, no_abort_on_missing_metadata: bool, filename_regex: Optional[str], no_abort_on_error: bool, no_abort_when_truncated: bool, no_abort_on_hydrus_import_failure: bool, no_force_add_metadata: bool, force_add_files: bool, subdir: Optional[str]) -> None:
    log.init(path, True)
    db.init(path)

    config_path = db.get_rootpath()+'/hydownloader-import-jobs.json'
    data_path = db.get_datapath()
    if config:
        config_path = config
    if not os.path.isfile(config_path):
        log.fatal("hydownloader-importer", f"Configuration file not found: {config_path}")

    jobs = json.load(open(config_path, 'r', encoding='utf-8-sig'))
    if not job in jobs:
        log.fatal("hydownloader-importer", f"Job not found in configuration file: {job}")
    jd = jobs[job]

    path_based_import = jd.get('usePathBasedImport', False)
    order_folder_contents = jd.get('orderFolderContents', 'default')
    non_url_source_namespace = jd.get('nonUrlSourceNamespace', '')

    effective_path = data_path
    if subdir is not None:
        # replace is to convert windows paths
        effective_path = effective_path + '/gallery-dl/' + unfuck_path_separator(subdir)

    client = hydrus_api.Client(jd['apiKey'], jd['apiURL'], session=get_session(5, 1))

    log.info("hydownloader-importer", f"Starting import job: {job}")

    # Counts for scanned files
    existing = 0
    imported = 0
    deleted = 0
    skipped = 0
    ignored = 0

    # Set of files which failed to import
    # Using a set to prevent duplicate entries when doing a dry run
    import_errors = set()

    # iterate over all files in the data directory
    for root, _, files in os.walk(effective_path):
        # sort files before iterating over them
        if order_folder_contents == "name":
            files = sorted(files)
        elif order_folder_contents == "mtime":
            files = sorted(files, key=lambda t: os.stat(root+'/'+t).st_mtime)
        elif order_folder_contents == "ctime":
            files = sorted(files, key=lambda t: os.stat(root+'/'+t).st_ctime)
        elif order_folder_contents != "default":
            printerr("The value of the orderFolderContents option is invalid", True)

        for fname in files:
            if skip_file(fname):
                ignored = ignored + 1
                continue

            abspath = root + "/" + fname
            path = os.path.relpath(abspath, start = data_path)
            if filename_regex and not re.match(filename_regex, path):
                if verbose: printerr(f"Skipping due regex mismatch: {path}", False)
                skipped = skipped + 1
                continue

            # set up some variables
            # some will be used later in the code, some are meant to be used in user-defined expressions
            ctime = os.stat(abspath).st_ctime
            mtime = os.stat(abspath).st_mtime
            split_path = os.path.split(path)
            fname_noext, fname_ext = os.path.splitext(fname)
            if fname_ext.startswith('.'): fname_ext = fname_ext[1:]

            is_file_in_import_db, db_mtime, db_ctime = db.check_import_db(path)
            if skip_already_imported and is_file_in_import_db:
                if not (no_skip_on_differing_times and (db_mtime != mtime or db_ctime != ctime)):
                    if verbose: printerr(f"Already imported, skipping: {path}...", False)
                    skipped = skipped + 1
                    continue

            # find the path of the associated json metadata file, check if it exists
            # for pixiv ugoira, the same metadata file belongs both to the .webm and the .zip,
            # so this needs special handling
            json_path = abspath+'.json'
            if not os.path.isfile(json_path) and abspath.endswith('.webm'):
                json_path = abspath[:-4]+"zip.json"
            json_exists = True
            raw_metadata = None
            if not os.path.isfile(json_path):
                json_exists = False
                import_errors.add(path)
                printerr(f"Warning: no metadata file found for {path}", not no_abort_on_missing_metadata)
            else:
                raw_metadata = open(json_path, "rb").read()

            generated_urls : set[str] = set()
            generated_tags : set[tuple[str, str]] = set()
            matched = False # will be true if at least 1 filter group matched the file
            json_data = None # this will hold the associated json metadata (if available)

            if verbose: printerr(f"Processing file: {path}...", False)

            # iterate over all filter groups, do they match this file?
            for group in jd['groups']:
                # evaluate filter, load json metadata if the filter matches and we haven't loaded it yet
                should_process = False
                metadata_only = group.get("metadataOnly", False)
                tag_repos_for_non_url_sources = group.get("tagReposForNonUrlSources", [])
                try:
                    should_process = eval(group['filter'])
                except:
                    import_errors.add(path)
                    printerr(f"Failed to evaluate filter: {group['filter']}", not no_abort_on_error)
                if not json_data and json_exists:
                    try:
                        json_data = json.load(open(json_path,encoding='utf-8-sig'))
                    except json.decoder.JSONDecodeError:
                        import_errors.add(path)
                        printerr(f"Failed to parse JSON: {json_path}", not no_abort_on_error)
                # add back the old "gallerydl_file_url" key if it does not already exist
                if json_data and not "gallerydl_file_url" in json_data:
                    potential_fileurl_keys= list(filter(lambda x: isinstance(x, str) and x.startswith("gallerydl_file_url_"), json_data.keys()))
                    if potential_fileurl_keys:
                        json_data["gallerydl_file_url"] = json_data[potential_fileurl_keys[0]]
                if not should_process:
                    # Don't count skipped here, this logic goes over all filter groups
                    continue
                if not metadata_only:
                    matched = True

                # get the data for this file from the additional_data db table and process it
                # set up some variables that user-defined expressions will be able to use
                additional_data_dicts = db.get_additional_data_for_file(path)
                if not additional_data_dicts and path.endswith('.webm'):
                    additional_data_dicts = db.get_additional_data_for_file(path[:-4]+"zip")
                extra_tags : defaultdict[str, list[str]] = defaultdict(list)
                min_time_added = -1
                max_time_added = -1
                for d in additional_data_dicts:
                    parse_additional_data(extra_tags, d['data'])
                    if min_time_added == -1 or min_time_added > d['time_added']:
                        min_time_added = d['time_added']
                    if max_time_added == -1 or max_time_added < d['time_added']:
                        max_time_added = d['time_added']
                sub_ids = []
                url_ids = []
                url_ids_int = []
                for d in additional_data_dicts:
                    if d['subscription_id']:
                        sub_ids.append(str(d['subscription_id']))
                    if d['url_id']:
                        url_ids_int.append(d['url_id'])
                        url_ids.append(str(d['url_id']))
                single_urls = []
                for item in db.get_queued_urls_by_id(url_ids_int, True):
                    single_urls.append(item['url'])

                # execute user-defined tag and url generator expressions
                for dtype, d in [('tag',x) for x in group.get('tags', [])]+[('url',x) for x in group.get('urls', [])]:
                    has_error = False
                    skip_on_error = d.get("skipOnError", False)
                    allow_empty = d.get("allowEmpty", False)
                    allow_no_result = d.get("allowNoResult", False)
                    allow_tags_ending_with_colon = d.get("allowTagsEndingWithColon", False)
                    rule_name = d.get("name")
                    generated_results = []
                    # if the expression is a single string
                    if isinstance(d["values"], str):
                        try:
                            eval_res = eval(d["values"])
                            # check result type: must be string or iterable of strings
                            if isinstance(eval_res, str):
                                generated_results = [eval_res]
                            else:
                                for eval_res_str in eval_res:
                                    if not isinstance(eval_res_str, str):
                                        import_errors.add(path)
                                        printerr(f"Invalid result type ({str(type(eval_res_str))}) while evaluating expression: {d['values']}", not no_abort_on_error)
                                    else:
                                        generated_results.append(eval_res_str)
                        except Exception as e:
                            import_errors.add(path)
                            if verbose and not skip_on_error:
                                printerr(f"Failed to evaluate expression: {d['values']}", False)
                                print(e)
                            has_error = True
                    else: # multiple expressions (array of strings)
                        for eval_expr in d["values"]:
                            try:
                                eval_res = eval(eval_expr)
                                # check result type: must be string or iterable of strings
                                if isinstance(eval_res, str):
                                    generated_results.append(eval_res)
                                else:
                                    for eval_res_str in eval_res:
                                        if not isinstance(eval_res_str, str):
                                            import_errors.add(path)
                                            printerr(f"Invalid result type ({str(type(eval_res_str))}) while evaluating expression: {eval_expr}", not no_abort_on_error)
                                        else:
                                            generated_results.append(eval_res_str)
                            except Exception as e:
                                import_errors.add(path)
                                if verbose and not skip_on_error:
                                    printerr(f"Failed to evaluate expression: {eval_expr}", False)
                                    printerr(e, not no_abort_on_error)
                                has_error = True

                    # check for empty results or failed evaluation, as necessary
                    if not generated_results and not allow_no_result and not has_error:
                        import_errors.add(path)
                        printerr(f"Error: the rule named {rule_name} yielded no results but this is not allowed", not no_abort_on_error)
                    if '' in generated_results and not allow_empty and not has_error:
                        import_errors.add(path)
                        printerr(f"Error: the rule named {rule_name} yielded an empty result but this is not allowed", not no_abort_on_error)
                    if dtype == 'tag' and not allow_tags_ending_with_colon:
                        for gentag in generated_results:
                            if gentag.strip().endswith(':'):
                                import_errors.add(path)
                                printerr(f"Error: the rule named {rule_name} yielded a tag ending with ':' ({gentag})", not no_abort_on_error)
                    if has_error:
                        if not skip_on_error:
                            import_errors.add(path)
                            printerr(f"Error: an expression failed to evaluate in the rule named {rule_name}", not no_abort_on_error)

                    # save results of the currently evaluated expressions
                    if dtype == 'url':
                        generated_urls.update(filter(lambda x: x, generated_results))
                    else:
                        if "tagRepos" in d: # predefined tag repos
                            for repo in d["tagRepos"]:
                                generated_tags.update((repo,tag) for tag in generated_results if tag)
                        else: # tag repos should be extracted from the tags
                            for tag in generated_results:
                                if not ":" in tag:
                                    import_errors.add(path)
                                    printerr(f"The generated tag '{tag}' must start with a tag repo name. In rule: {rule_name}.", not no_abort_on_error)
                                else:
                                    repo = tag.split(":")[0]
                                    actual_tag = ":".join(tag.split(":")[1:])
                                    if actual_tag: generated_tags.add((repo,actual_tag))
            if matched:
                printerr(f"File matched: {path}...", False)

                if not os.path.getsize(abspath):
                    import_errors.add(path)
                    printerr(f"Found truncated file, won't be imported: {abspath}", not (no_abort_on_error or no_abort_when_truncated))
                    continue

                generated_urls_filtered : list[str] = []
                invalid_url_tags = []
                for url in generated_urls:
                    url = url.strip()
                    if is_valid_url(url):
                        generated_urls_filtered.append(url)
                    elif url:
                        if verbose:
                            printerr(f"Invalid source URL: {url}", False)
                        for repo in tag_repos_for_non_url_sources:
                            invalid_url_tags.append((repo,non_url_source_namespace + ':' + url if non_url_source_namespace else url))
                generated_tags.update(invalid_url_tags)
                generated_urls_filtered = sorted(generated_urls_filtered)

                if verbose:
                    printerr("Generated URLs:", False)
                    for url in generated_urls_filtered:
                        printerr(url, False)
                    printerr("Generated tags:", False)
                    for repo, tag in sorted(list(generated_tags), key=lambda x: x[0]+x[1]):
                        printerr(f"{repo} <- {tag}", False)

                # calculate hash, check if Hydrus already knows the file
                if verbose: printerr('Hashing...', False)
                already_added = False
                hexdigest = str()
                if do_it:
                    hasher = hashlib.sha256()
                    with open(abspath, 'rb') as hashedfile:
                        buf = hashedfile.read(65536 * 16)
                        while len(buf) > 0:
                            hasher.update(buf)
                            buf = hashedfile.read(65536 * 16)
                    hexdigest = hasher.hexdigest()
                    if any(map(lambda x: x.get("is_local", False), client.get_file_metadata(hashes=[hexdigest]))):
                        printerr("File is already in Hydrus", False)
                        existing = existing + 1
                        already_added = True
                if verbose: printerr(f'Hash: {hexdigest}', False)
                # send file, tags, metadata to Hydrus as needed
                if not already_added or force_add_files:
                    if verbose: printerr("Sending file to Hydrus...", False)
                    if do_it:
                        response: dict
                        # import the file, get the response
                        if path_based_import:
                            response = client.add_file(abspath)
                        else:
                            response = client.add_file(io.BytesIO(open(abspath, 'rb').read()))

                        # update counts based on result, existing is checked for previously
                        if response['status'] == 1:
                            imported = imported + 1
                        elif response['status'] == 3:
                            printerr(f'Failed to import, file is deleted!', False)
                            deleted = deleted + 1
                        elif response['status'] > 3:
                            import_errors.add(path)
                            printerr(f'Failed to import, status is ' + str(response['status']), not (no_abort_on_error or no_abort_on_hydrus_import_failure))
                if not already_added or not no_force_add_metadata:
                    if verbose: printerr("Associating URLs...", False)
                    if do_it and generated_urls_filtered: client.associate_url(hashes=[hexdigest],urls_to_add=generated_urls_filtered)
                    if verbose: printerr("Adding tags...", False)
                    tag_dict = defaultdict(list)
                    for repo, tag in generated_tags:
                        tag_dict[repo].append(tag)
                    if do_it:
                        client.add_tags(hashes=[hexdigest],service_names_to_tags=tag_dict)
                if verbose: printerr("Writing entry to import database...", False)
                if do_it:
                    db.add_or_update_import_entry(path, import_time=time.time(), creation_time=ctime, modification_time=mtime, metadata=raw_metadata, hexdigest=hexdigest)
                    db.sync()

            else:
                skipped = skipped + 1
                if verbose: printerr(f"Skipping due to no matching filter: {path}", False)

    log.info("hydownloader-importer", f"Finished import job: {job}")
    total = existing + imported + deleted
    log.info("hydownloader-importer", f"imported: {imported}")
    log.info("hydownloader-importer", f"existing: {existing}")
    log.info("hydownloader-importer", f" deleted: {deleted}")
    log.info("hydownloader-importer", f"   total: {total}")
    log.info("hydownloader-importer",  "---------------")
    log.info("hydownloader-importer", f" skipped: {skipped}")
    log.info("hydownloader-importer", f" ignored: {ignored}")
    log.info("hydownloader-importer", f"     all: {total + skipped + ignored}")
    log.info("hydownloader-importer", "---------------")
    if len(import_errors) == 0:
        log.info("hydownloader-importer", f"{len(import_errors)} Files Failed to Import")
    else:
        log.warning("hydownloader-importer", f"{len(import_errors)} File(s) Failed to Import")
    for fname in import_errors:
        log.warning("hydownloader-importer", fname)

    db.shutdown()

def main() -> None:
    cli()
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()

if __name__ == "__main__":
    main()
