# hydownloader tutorial introduction

TODO: mention to read the README before this

## Installation and configuration

TODO: mention multiinstance, oauth, how to use command line help (--help, command --help), gallery-dl configs

### hydownloader

### hydownloader-systray

TODO: clarify archive/delete in systray

### Hydrus Companion

## Exporting data from Hydrus to hydownloader

## Downloading

### Single URLs

### Subscriptions

## Management and maintenance

### Subscription checks

### Logs

### Self-tests

### Reports

### Other tools

## Importing downloaded data into Hydrus

### Overview

Importing downloaded files into Hydrus is not done automatically. The `hydownloader-importer` tool serves this purpose. The importer tool works by running import jobs.
Import jobs are defined in a JSON configuration file.
A job contains configuration telling the importer exactly which files to import and how to generate tags and URLs from the JSON metadata files that were created by the downloader.
Since different sites have different metadata JSON formats, rules must be created for each site individually. hydownloader comes with a sample job that has rules
for all sites that hydownloader natively supports. The default name for the configuration file is `hydownloader-import-jobs.json`.
You can adjust this file so that tags and URLs are generated how you want them.

Note that by default, `hydownloader-importer` works in simulation mode: it will do all the file scanning and metadata processing but will not do the final step of actually
sending the files to Hydrus. This is very useful, as it is a good way to find problems that would interrupt an actual import job. Such problems can include
new or changed metadata format which breaks some rules in the job configuration, truncated files caused by sudden interruption or other data loss, or simply
wrong/unwanted generated tags and URLs. By default, the importer stops if a problem is detected. There are command line flags to control this behavior and also
to print all generated tags and URLs for inspection. You can also restrict the importer to a specific filename or filenames matching a pattern (useful for testing without
getting flooded by all the generated output).

`hydownloader-importer` also saves the hash of imported files, the date of import and the raw file metadata into its database when a file is imported.
This is necessary so that it can know which files were already imported and skip those. The stored metadata also makes it possible to generate new or different metadata
for already imported files.

You can start using the importer by running the `default` job. Use the `--verbose` flag to display the matching files and generated metadata.
After this, you should customize the import job configuration to your liking. It is recommended to start by looking at the default configuration and
experimenting by modifying it. The format is also documented below.

As usual, for all details and capabilities of the importer tool, refer to the command line help. It is highly recommended to read through the help for the command
you want to run before actually running it.

### Configuration format

Note: The best way to understand how to write or modify import rules is to look at the default ruleset and check this reference as needed.

The format of the importer configuration JSON is the following: the top level object contains the individual job configurations.
The keys are the names of the jobs. Each job can have the following top level keys:

- `apiURL` and `apiKey` strings. The URL and access key for the Hydrus API.
- `forceAddFiles` and `forceAddMetadata` booleans. These control whether files and metadata should be imported even if the current file is already in Hydrus.
- `usePathBasedImport` boolean. If true, the absolute path of the file to be imported is sent to the Hydrus import API. If false, the file data is sent in the request instead of the path. If the Hydrus instance and the hydownloader data is not on the same machine, path based import won't work.
- `orderFolderContents`, one of `"name"`, `"ctime"`, `"mtime"` or `"default"`. This specifies the order the importer shall process files in a folder. `"name"` means the files are sorted in alphabetical order, while `"ctime"` and `"mtime"` sorts by the creation and modification time, respectively. `"default"` uses the system-specific default traversal order.
- `groups` is a JSON list of rule groups. A rule group contains a filter which decides what files it will be used for and rules for generating tags and URLs. A file can match multiple rule groups and only files that match at least 1 group will be imported.

In the default configuration, each site has its own rule group. A rule group is a JSON object that contains the following keys:

- `filter`: a Python expression (as a string) that decides whether a given filename matches this group or not. The evaluation of the expression must result in either `True` or `False`.
- `metadataOnly` boolean. If set to true, this rule group won't be counted as matching for the purpose of deciding which files to import. Useful for setting up general rules that match any file.
- `tags` a JSON list of tag rule objects.
- `urls` a JSON list of URL rule objects.

A tag rule object is a JSON object that can contain the following keys:

- `name` a string, the program will refer to this rule object by using this name (e.g. in error messages).
- `allowNoResult` boolean. If true, this rule object not yielding any tags will not be considered an error.
- `allowEmptyResult` boolean. If true, this rule object yielding empty tags (that is, a string of length 0) will not be considered an error. Such tags will be ignored.
- `allowTagsEndingWithColon` boolean. If true, this rule object yielding tags ending in a `:` character will not be considered an error.
- `tagRepos` list of strings. The tag repos where the tags generated by this rule object should be added. It is also possible to dynamically generate the list of tag repos too with the tags. To do this, omit the `tagRepos` key and prefix all generated tags with their target tag repo as namespace (e.g. `my tags:title:whatever` means that the `title:whatever` tag should be added to `my tags`).
- `values`: either a Python expression (as a string) or a list of Python expressions (as a list of strings). Each expression, when evaluated, must result either in a string or an iterable of strings. These will be the generated tags.

URL rule objects work the same way as tag rule objects and can have the same keys (except `allowTagsEndingWithColon` and `tagRepos` which don't make sense for URLs).

In the above description, a "Python expression" refers to a snippet of Python code that yields some value, stored as a JSON string. These snippets are evaluated during the import to
generate tags and URLs (the evaluation is done by using Python's `eval` function). There are some predefined values and helper functions you can use in these snippets
to make generating metadata easier. For examples, look at the default configuration.

List of available Python variables and their types:

- `json_data: dict`: JSON metadata for the currently imported file, as parsed by Python's `json.load`.
- `abspath: str`: full absolute path of the current file.
- `path: str`: relative (to the hydownloader data directory) path of the current file.
- `ctime: float`: creation time of the current file.
- `mtime: float`: modification time of the current file.
- `split_path: list[str]`: components of the relative path as a list of strings.
- `fname: str`: name of the current file.
- `fname_noext: str`: name of the current file, without extension.
- `fname_ext: str`: extension of the current file (without the leading dot).
- `sub_ids: list[str]`: IDs of hydownloader subscriptions the current file belongs to.
- `url_ids: list[str]`: IDs of hydownloader URL downloads the current file belongs to.
- `extra_tags : dict[str, list[str]]`: holds tags extracted from the `additional_data` field of the hydownloader database. The keys are namespaces, the values are the tags belonging to the given namespace. Unnamespaced tags use the empty string as key.

List of available helper functions:

- You can use functions from the `os`, `re`, `time`, `json`, `hashlib`, `itertools` modules. These are pre-imported before expressions are evaluated.
- `clean_url(url: str) -> str`: cleans up URLs (e.g. removing duplicate `/` characters from paths).
- `get_namespaces_tags(data: dict[str, Any], key_prefix : str = 'tags_', separator : Optional[str] =' ') -> list[tuple[str,str]]`
