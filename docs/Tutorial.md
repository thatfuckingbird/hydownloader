# hydownloader tutorial introduction

This document aims to walk you through the installation, configuration and usage of hydownloader and related applications.
Before reading further, you should read the [README](../README.md) first which contains the most basic information about hydownloader which won't be repeated here.

## Installation and configuration

### hydownloader

hydownloader is a command line application written in Python. The easiest way to install and use it is to install Python, clone this repo, then use the `poetry` package manager
for installing dependencies and running hydownloader itself. The [README](../README.md) contains step-by-step instructions on how to do this.

hydownloader consists of multiple command line applications: `hydownloader-daemon` is the main application that runs in the background and handles downloading. The actual
downloading is done by [gallery-dl](https://github.com/mikf/gallery-dl/), which `hydownloader-daemon` runs and controls as needed.
There is `hydownloader-importer` for adding downloaded files with metadata to Hydrus, `hydownloader-tools` provides various utilites that can run independently from the main daemon and so on...
The [README](../README.md) has more information on the different parts and what they are good for.
All the applications follow the same basic command line argument format. The first command line argument is always a command (or `--help` to just list available commands).
This is followed by parameters to that command. The order of the parameters is arbitrary, but they must come after the command. To get a list of all available parameters
and their explanations for a command, call the command with the `--help` parameter. For example in the command line `hydownloader-importer run-job --help`,
`run-job` is the command and the only parameter for it is `--help`. Executing this command line will list all the flags and parameters that work with the `run-job` command.
Knowing about the available options is essential for getting the results you want out of hydownloader.
It is very important to use `--help` first to familiarize yourself with the various commands and their parameters as most parameters are not detailed here or in the [README](../README.md).

Similarly to Hydrus, hydownloader stores all its data and configuration in a self-contained and portable database folder.
All hydownloader commands need to receive the path to the database folder as a command line argument. This setup means that it is very easy to
have multiple independent instances of hydownloader, even running at the same time.

After you have installed hydownloader and confirmed it works, the next step is to configure it.
This is done through the configuration found in the database directory. hydownloader creates these files with their default values when
initializing a new database directory. At the very least you probably want to check `hydownloader-config.json` to set the access key and
a few other basic options. `hydownloader-import-jobs.json` contains the rules `hydownloader-importer` will use to generate tags and URLs for Hydrus, see later sections for more on this.
Note that you have to run `hydownloader-importer` yourself to add downloaded files and their metadata to Hydrus. hydownloader does not do this automatically,
as technically Hydrus is not necessary to use hydownloader. There are two gallery-dl configuration files: `gallery-dl-user-config.json` and `gallery-dl-config.json`.
These use gallery-dl's options and configuration format, see their [documentation](https://github.com/mikf/gallery-dl/blob/master/docs/configuration.rst) for more info. Generally you can freely modify `gallery-dl-user-config.json` (and this is the place to specify usernames, passwords and other site-specific options),
but only change `gallery-dl-config.json` if you know what you are doing - modifying the options there could break the communication between hydownloader and gallery-dl.
Note that changes to the gallery-dl configuration files will be applied on the next download or subscription check, so you don't have to restart hydownloader to apply them,
but of course they won't apply to the already running URL download and subscription check.

Some sites also need cookies to access login-gated content. These should be added to `cookies.txt` in the database folder. While you can edit this manually,
it is usually better to use some tool to export cookies in the right format (for example Hydrus Companion can do this).
Generally, you should do all configuration while `hydownloader-daemon` is not running.

For some sites (most importantly, pixiv), neither passwords nor cookies are sufficient and OAuth-based login is needed. This usually means
you have to acquire an OAuth token using your browser (possible copying the token out of the dev tools) and then adding this token to the gallery-dl configuration.
To make this process easier, `hydownloader-tools` has commands to acquire OAuth tokens for some of these sites (like pixiv).
See the `--help` of `hydownloader-tools` for what's available. Upon running the command, your browser should open the right login page
and instructions will be displayed on what to do. Note that usually these OAuth tokens expire in a few seconds, so you have to be fast with copying the token
from your browser into the command line.

`hydownloader-tools` also contains a test command with many sites supported, which you can run any time and will tell you whether hydownloader
can successfully download login-gated content for the selected sites and that metadata is saved correctly. It is recommended to run tests for sites you use once in a while to make sure everything
is working as it should.

As a last step in the configuration, you might want to export URLs from your Hydrus database to the hydownloader database.
This serves two purposes: for supported sites, hydownloader will recognize URLs of files you already have in your Hydrus database and will avoid
re-downloading those files. Secondly, `hydownloader-daemon` will be able to give URL information through its API similarly to the Hydrus API.
This makes it possible for external applications like Hydrus Companion to use this API instead of the Hydrus API for providing features like HC's inline link lookup.

The URL export is done through the `hydownloader-anchor-exporter` tool. For information on how to use this tool, see its `--help` output. Make sure you review
all the available command line parameters and their explanations there before running it. While it is safe to use as it only ever opens the
Hydrus database in read-only mode, the correct command line parameters must be set depending on what URLs you want to export and which of the
two previously mentioned use cases is relevant for you. Note that on large Hydrus databases, running this tool can lead to high (multiple gigabytes)
memory usage temporarily (but generally the runtime shouldn't be more than a few minutes).

Finally, an advanced topic is running multiple instances of hydownloader in a way that they use the same database.
This makes it possible to avoid downloading files already downloaded by other instances and save files from all instances to the same location.
The [README](../README.md) contains a section on this, but usually you will only need it if you scrape the full content of multiple sites, as a single instance
of hydownloader can deal with thousands of subscriptions and single URL downloads. Note that running multiple, completely independent instances is also easy to do just by using
different database folders, so if your instances download from separate sites then you don't really need this either.

### hydownloader-systray

After installing and configuring hydownloader, you need some way to actually access its features like adding/managing URLs and subscriptions.
Since the hydownloader daemon runs in the background and is accessible through a HTTP API, it would be very inconvenient having to directly interact with it.
[hydownloader-systray](https://github.com/thatfuckingbird/hydownloader-systray) is an easy to use, multiplatform GUI application for managing hydownloader.
You tell it the address that the hydownloader daemon uses and your access key, and it will provide an interface for URLs, subscriptions, subscription check history
and logs. You can add and delete URLs and subscriptions and change their various properties. It also displays the current status
of the hydownloader daemon (what it is doing currently, how many subs and URLs are queued). Some management actions are also accessible.
Read the documentation at the [hydownloader-systray](https://github.com/thatfuckingbird/hydownloader-systray) repo on how to install, configure and use it.

### Hydrus Companion

You can use hydownloader as the backend for the [Hydrus Companion](https://gitgud.io/prkc/hydrus-companion) browser extension.
While originally made for Hydrus, it also supports hydownloader now with mostly the same feature set.

Hydrus Companion has many features that make downloading easier as you browse the web. Among them are sending URLs and pages directly from your browser to hydownloader for downloading,
adding and managing hydownloader subscriptions from your browser, highlighting already known/downloaded URLs on webpages ("inline link lookup") and many more.

Extensive documentation on how to configure the extension to work with hydownloader and on all the available features is included in the extension itself.
See also the README in the linked git repository.

## Exporting data from Hydrus to hydownloader

Currently you can export URLs from Hydrus to hydownloader in order to avoid redownloading files you already have in your Hydrus database and to
provide URL information for services such as the inline link lookup in Hydrus Companion. This is done by using the `hydownloader-anchor-exporter` tool
as detailed in the [Installation and configuration](installation-and-configuration) section.

To avoid redownloading already downloaded files, so-called "anchors" (hence the "anchor exporter" name) are stored in a database,
that identify a specific post on a specific website. For example, an anchor entry of `gelbooru4977152` identifies the post with number 4977152 on gelbooru.
If this is found in the anchor database, the content won't be downloaded again.
For supported sites, `hydownloader-anchor-exporter` can generate these anchors from post URLs stored in your Hydrus database
(you can find the list of supported sites in the `--help` of the anchor exporter tool). It is also possible to selectively generate anchors only for some files.

For URL information services (e.g. the inline link lookup in Hydrus Companion), it is not enough to store these anchors, but all
URLs known to Hydrus should be exported to the hydownloader database. This can be done with the `--fill-known-urls` argument.
Alongside the URLs, the file status (whether the files belonging to the URLs are deleted or not) is also exported.

If, beside hydownloader, you also use Hydrus for downloading, or you use the URL information APIs of hydownloader, then you should periodically
re-run the anchor exporter tool to update URL information in your hydownloader database based on the changes in your Hydrus instance.

You should check the `--help` of `hydownloader-anchor-exporter` for more information and advanced features which are not documented here.

## Downloading

There are two main ways to download with hydownloader: single URL downloads and subscriptions. Single URLs are one-off downloads: you give hydownloader a URL
and it will download all content it finds there, then stop. Subscriptions are repeated downloads from the same site, where the aim is to get all new
content since the last check. Subscriptions usually work on galleries (like images uploaded by an artist or the result of a tag search).

Both for single URL downloads and subscriptions, gallery-dl must support the site you want to download from (direct links to files also work).
For each individual subscription or single URL download, you can configure several properties governing the download process, e.g. whether to overwrite existing files
or how often to check a subscription for new files.

### Single URLs

When you send a URL for downloading to the hydownloader daemon, it will get added to the download queue.
hydownloader periodically checks this queue and downloads any URLs that were not yet downloaded.
Already downloaded URLs remain in the database so you can review your URL download history, redownload them, etc.

Each URL has various properties associated with it, which control the download process.
These are visible in (and can be changed from) hydownloader-systray. It is very important to understand what these properties
do as they can drastically affect the behavior of hydownloader and the download results.

These are the properties associated with each URL (the most important ones with bold names):

| Name | Value | Explanation |
|-------|---------|---------|
| **ID** | integer | A unique numeric ID identifying this URL entry in the database (not user editable). |
| **URL** | text | The URL to download. |
| Priority | number | The priority of this URL. Entries with higher priority will be downloaded first (default is 0). |
| Ignore anchor | boolean | If set to true, the anchor database will not be used when downloading this URL, meaning that even if it is known to hydownloader, it will be downloaded again (unless the previously downloaded files are still there and overwrite is not enabled). |
| Overwrite existing | boolean | Overwrite existing downloaded files, if there is any. The default behavior is to skip. |
| **Additional data** | text | This field holds metadata like additional tags you want associated with files downloaded from this URL. Currently you can write tags here separated by commas. Hydrus Companion also saves its generated metadata and tags here. More formats might be supported in the future. |
| **Status** | integer | Numerical status of this URL entry. -1 means not yet processed (this is how hydownloader finds the entries it needs to download), 0 means successfully downloaded. Higher values mean some kind of error happened during the download (see the result status field). |
| Result status | text | The status of the download, as text (either 'ok' or the error description if the download errored). Set by hydownloader after the download is finished. If there was an error, checking the log belonging to this URL entry will usually tell you the details. |
| Time added | datetime |The time the URL was added to the hydownloader database. Written by hydownloader, not user editable. |
| Time processed | datetime | The time the URL was processed (downloaded) by hydownloader. Written by hydownloader, not user editable. |
| **Paused** | boolean | Paused URLs won't be downloaded. You need to unpause the URL before hydownloader will process it. |
| Metadata only | boolean | Only generate metadata files, do not download media. |
| Filter | text | This will be used as the value for the `filter` option of gallery-dl. Can be used to filter what is downloaded based on file type or other properties (depending on what the site supports). See the gallery-dl documentation for more info on filters. |
| Max files | integer | Maximum number of files to download from this URL. By default, there is no limit. |
| New files | integer | Number of new files downloaded from this URL (not including metadata files). Written after the download is done, not user editable. |
| Already seen files | integer | Number of files on this URL that were already previously downloaded. Written after the download is done, not user editable. |
| Comment | text | You can write any additional notes for yourself in this field. It will not be processed by hydownloader. |
| Archived | boolean | Clients connecting to hydownloader (like hydownloader-systray) will not list archived URLs by default. This does not affect the working of hydownloader itself in any way, but is used so that you can hide old URLs you are done with from the GUI (and reduce network traffic when requesting the list of URLs). (This has no relation to the inbox/archive status in Hydrus.) |

If you want to change some of these properties before the download happens, it is best to add the URL as paused,
do the changes, then unpause it.

Note that deleting URLs only means that their entry is removed from the database table that holds the URL queue.
All the downloaded files, logs, etc. will remain.

### Subscriptions

For subscriptions, hydownloader has additional support for some sites beyond what gallery-dl provides. This additional support includes recognizing URLs that are
subscribable and extracting keywords from them. This makes it possible to store these subscriptions not as URLs, but as a downloader plus keywords pair,
making subscription management much nicer and allowing for features such as directly adding subscriptions from your browser via Hydrus Companion.

You can still subscribe to sites that gallery-dl supports but hydownloader does not recognize the URL as subscribable, by using the `raw` downloader. For this downloader, the keywords field
should contain the full URL for the gallery you want to subscribe to.

Subscriptions keep track of already downloaded sites by using the previously mentioned anchor database. This database is shared for the whole hydownloader instance,
which means that it is safe to have multiple subscriptions that potentially yield the same files. These will be downloaded only once (for the first subscription that finds them).

Just like with URLs, subscriptions also have several properties to control how hydownloader processes them.
It is essential to understand these to be able to effectively utilize the subscription feature.

These are the properties associated with each subscription (the most important ones with bold names):

| Name | Value | Explanation |
|-------|---------|---------|
| **ID** | integer | A unique numeric ID identifying this subscription in the database (not user editable). |
| **Downloader** | text | The site to download from, or `raw`. See the explanation above. |
| **Keywords** | text | The search keywords. See the explanation above. |
| Priority | number | Same as for single URLs. |
| **Paused** | boolean | Same as for single URLs. |
| **Check interval** | integer | How often should hydownloader check for new files. **Value is in seconds.** |
| **Abort after** | integer | Stop looking for new files after this many consecutive already seen files were encountered. |
| **Max files (regular check)** | integer | Maximum number of files to download on a regular check. |
| **Max files (initial check)** | integer | Maximum number of files to download on the first check of this subscription (applies when "last check" is empty). |
| Last check | datetime | When was this subscription last checked for new files (successfully or not). A subscription check will be considered an "initial check" if and only if this field is not set when the check starts. Clearing this field will make hydownloader treat the subscriptin as if it were never checked before. |
| Last successful check | datetime| When was the last check of this subscription that didn't have any errors. |
| **Additional data** | text | Same as for single URLs. |
| Time created | datetime | The date and time when this subscription was created. |
| Filter | text | Same as for single URLs. |
| Comment | text | Same as for single URLs. |

Note that deleting subscriptions only means that their entry is removed from the database table that holds subscriptions.
All the downloaded files, logs, etc. will remain.

#### Important note on sudden shutdowns in the middle of large subscription checks

`hydownloader-daemon` is usually resilient to sudden shutdowns and network errors, with the exception that if it happens to be terminated in the middle of a large subscription check,
then subsequent checks might miss older not-yet-downloaded files (as it sees that there are many already downloaded files and stops searching).

You can work this around either by increasing the number of required consecutive already-seen files to stop searching (configurable for each subscription),
or by manually queueing a one-off download with a high stop threshold if you know that a specific subscription might be affected.
If the number of already-seen files required to stop is larger than the amount a single check of the subscription
can ever produce then of course this problem can never occur.

However, this problem only really affects very fast moving subscriptions that regularly produce a large number of files.
To prevent this problem, you can make hydownloader check these subs more often and increase the number of already-seen files required to stop searching.

Doing graceful shutdowns (hit Ctrl+C in the terminal window where `hydownloader-daemon` is running
or use the shutdown command in the `hydownloader-systray` GUI) will also avoid this problem, since if shut down this way, hydownloader will always
finish the currently running subscription and URL download before actually shutting down.

Even if you do not have subs that might be affected, doing a graceful shutdown and letting hydownloader finish whatever it is currently doing first
is always better than just suddenly terminating it.

## Management and maintenance

hydownloader saves large amounts of additional information (logs and subscription check history) and provides tools to analyze this information in order
to find and diagnose download problems. This is especially important for subscriptions, where problems could easily go unnoticed for a long time with subscriptions
producing no files.

### Subscription checks

A history of checks for all subscriptions is stored in the database. For each check, you can view the time, status (whether there was any error) and the number
of new/already seen files. `hydownloader-systray` can display check history for a single subscription or for all subscriptions.
Old entries can also be archived, which works the same way as for single URL queue entries.

### Logs

hydownloader stores the following logs:

- A main log (daemon log), generated by `hydownloader-daemon` and the other hydownloader components. This log records various events (startup, shutdown, subscription checks, downloads, etc.) and
any problems (warnings, errors). This is stored as `daemon.txt` in the `logs` subfolder of your hydownloader database folder.
- A log file for each subscription. This is generated by gallery-dl and has information about the details of the download process and any network problems.
- A log file for each single URL download. Same content as the subscription log.
- Unsupported URLs (these are URLs that gallery-dl encountered but could not handle) are also stored in separate text files for each single URL download and subscription.

All logs are stored as text files in the `logs` subfolder of your hydownloader database folder. You can use `hydownloader-systray` to view and search/filter them.

### Download tests

One of the primary principles in making hydownloader was that it should not only provide a download system, it should provide
a **correct** one. This means that it should retrieve all requested files, with as much (correct) metadata as possible and
that it should be easy to notice and diagnose problems as they happen. It also means that it should be able to test
downloading from various sites and that these downloads indeed produce the expected results (including metadata).
These features are especially helpful when sites change in ways that break downloading.

Beyond the previously explained logging features, `hydownloader-tools` also has a built-in test feature.
This will attempt to download from the selected sites, using your hydownloader configuration and will check the results against known-good ones.
The test downloads use your hydownloader configuration but will use the `test` directory instead of the regular data directory and a separate
anchor database (also under ṫhe `test` directory), so you can safely run these tests without it affecting your usual downloads.

There is also a special, non-download test called the `environment` test. Instead of downloading, this will check
whether all the dependencies of hydownloader are installed and that the versions are compatible.

The `test` directory is cleaned before every test download, and also after every successful one. When a test download fails,
the cause of failure will be printed to the main log (and to the command line) and the `test` directory is left intact.
You can then inspect the download logs, any downloaded files and the anchor database there to diagnose issues.

The test feature is accessible through the `test` command of `hydownloader-tools`. See the `--help` for this command for the
list of supported sites and various other options.

It is recommended to periodically run tests for sites you usually download from, just to make sure everything is still working as it should.

### Reports

The previously introduced `test` command helps to ensure downloading is working as it should.
However, it cannot find problems with your local URL download queue and subscriptions.

The `report` command (also in `hydownloader-tools`) was created to help you find failing or otherwise misbehaving subscriptions
and URLs. For example, a subscription might not be producing any more files because the artist deleted or moved the gallery,
or it could be repeatedly failing checks for some other reason.

The report calculates and prints various statistics (to the command line and the main log) aimed to detect misbehaving subscriptions and
single URLs (like "subscriptions that didn't error but produced no files", or "subscriptions/URLs due for download for too long without actually being processed", and many others).
You can also control how verbose the report is with the various parameters of the `report`˙command (as usual, see the `--help` for more on these).

It is recommended to periodically run and review the report to ensure that all your URLs and subscriptions are being downloaded as they should be.

### Other tools

There are also some other commands found in `hydownloader-tools` to help with some specific or rare situations (logging into pixiv, mass adding subscriptions or URLs, etc.).
Check the `--help` to see what is available.

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
- `nonUrlSourceNamespace` string. If a generated URL is invalid (typically occurs when people type non-URLs into the source field of boorus), it will be added as a tag instead. This is the namespace where such tags go (or leave empty for unnnamespaced). See `tagReposForNonUrlSources` later for more on this feature.
- `groups` is a JSON list of rule groups. A rule group contains a filter which decides what files it will be used for and rules for generating tags and URLs. A file can match multiple rule groups and only files that match at least 1 group will be imported.

In the default configuration, each site has its own rule group. A rule group is a JSON object that contains the following keys:

- `filter`: a Python expression (as a string) that decides whether a given filename matches this group or not. The evaluation of the expression must result in either `True` or `False`.
- `metadataOnly` boolean. If set to true, this rule group won't be counted as matching for the purpose of deciding which files to import. Useful for setting up general rules that match any file.
- `tagReposForNonUrlSources` list of strings. List of tag repos to send tags generated from invalid URLs to. Leave empty or remove to not add tags based on invalid URLs.
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
