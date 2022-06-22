# hydownloader

Alternative download system for Hydrus.

## What is this and how does it work?

This is a set of utilites that provide a Hydrus-like download system outside of Hydrus, based on [gallery-dl](https://github.com/mikf/gallery-dl/).
The main component is a daemon that runs in the background and uses a database of subscriptions and URL data
to control gallery-dl. It downloads files into a separate folder, independently of Hydrus. It also saves
detailed metadata, checks for download errors, keeps track of already downloaded files and provides
other features expected from a complete downloader system.

There are separate tools to export known URLs from Hydrus to avoid re-downloading files you already have in your
Hydrus database and also for importing downloaded files into Hydrus with metadata. The identifiers of already seen files
are stored in a database and are known as "anchors" in hydownloader.

The daemon provides a JSON-based API, which is the primary means of controlling it and querying information from it.

## WARNING: GUI not included

hydownloader is a server/command line application. There is no graphical interface included. It provides a HTTP API, but this is not meant to be directly used by humans.
**There is a separate GUI application to manage hydownloader, called hydownloader-systray. [It has its own separate repository here](https://github.com/thatfuckingbird/hydownloader-systray).
This is the recommended way to manage your hydownloader instances.**

## How does it compare to the Hydrus downloader system?

The main differences:

* Different target audience. Generally meant for people who have an idea what they are doing and can use a command line. Less handholding, no GUI for editing downloaders.
* Downloads to separate location, files must be imported to Hydrus by the user (there is a tool to make this easy).
* The downloaders are written in Python (provided by gallery-dl), and thus are not user-installable or editable, but are also more powerful.
* More detailed metadata extraction (saves metadata types that are currently not supported by the Hydrus downloader system).
* Ugoira support with lossless conversion (thanks to gallery-dl).
* Can download any type of file, not restricted to Hydrus-supported mimes.
* Better error handling and reporting, suitable for managing a large number of subscriptions and URL downloads.
* Subscriptions are checked on a fixed (set by the user) time interval, no adaptive check timing like in Hydrus.
* There is no direct equivalent of the Hydrus "thread watcher" feature, though it can be replicated with subscriptions with short check timing.

**WARNING: Making a downloader system that works with many sites, does not lose/skip files or metadata and correctly handles error conditions is a complex problem.
Accordingly, hydownloader is also a complex application that requires investing time and effort to learn. If you are not willing to read documentation and learn, you are better off finding some simpler, less powerful solution.**

## Installation

0. Install Python 3.9 or newer. On Windows, make sure you install from the official Python site. If the installers asks you whether it should add the Python executable to PATH say yes.
1. Open a command line. Type `python --version`. It should output the version number, which should be 3.9 or newer.
2. Install ffmpeg. On Linux, it should be easy through the package manager, for Windows the official ffmpeg site has binaries but make sure that they are added to the PATH (so that you can invoke `ffmpeg` in the command line).
3. Type `python -m pip install poetry --user`. This should install the poetry package manager. If you are on Linux, you can likely omit the `python -m` from this and all following commands.
4. Clone this repo.
5. Navigate into the cloned repo folder in the command line.
6. Type `python -m poetry install`. This should install hydownloader.
7. To run hydownloader components like `hydownloader-daemon`, prefix all commands with `python -m poetry run`. Example: `python -m poetry run hydownloader-daemon start --path /path/to/data/folder`.
Alternatively, you can type `python -m poetry shell` and then you can run subsequent commands without the `python -m poetry run` prefix.

## How to use - overview (READ AND UNDERSTAND THIS BEFORE ASKING FOR SUPPORT)

This section will give you a basic overview of hydownloader. After reading this, you might want to check out
the [Tutorial](docs/Tutorial.md). There is also a [FAQ](docs/FAQ.md) and [API docs](docs/API.md).

The main components:

* `hydownloader-importer`: imports downloaded files and metadata into Hydrus.
* `hydownloader-anchor-exporter`: scans a Hydrus database and adds anchors from identified file/post URLs to the hydownloader database.
* `hydownloader-daemon`: the main service that does the downloading (by running gallery-dl) and provides the API.
* `hydownloader-tools`: various command line utilies.

All of the above scripts can be run from the command line. Run them with the `--help` argument to list the available commands for each script.
Generally, the first step is to decide on the database location (this will contain the hydownloader database, auxiliary config files and also downloaded data and metadata).
The first time you run hydownloader-daemon or hydownloader-tools, it will initialize a database at the given location. The database
concept is similar to what Hydrus does: all files are contained within the database folder, which can be freely relocated when hydownloader is not running.
After initializing the database, you might want to customize `hydownloader-config.json`, most importantly by setting the API access key (do this while
hydownloader is NOT running).

Contents of a hydownloader database folder:

* `test/`: directory used when running tests
* `temp/`: temporary directory (DO NOT TOUCH)
* `logs/`: log files
* `data/`: downloaded files and metadata
* `hydownloader.db`: the main hydownloader database, mostly storing subscriptions and the URL queue (use the API, avoid direct editing)
* `hydownloader.shared.db`: the parts of the hydownloader database that can be shared between multiple running instances (avoid direct editing)
* `cookies.txt`: stores cookies used for downloads (use the API to add cookies, do not edit directly)
* `anchor.db`: anchor database (DO NOT TOUCH)
* `gallery-dl-cache.db`: gallery-dl cache to store session keys and similar (DO NOT TOUCH)
* `gallery-dl-config.json`: gallery-dl configuration file with settings needed for correct hydownloader operation (DO NOT TOUCH)
* `gallery-dl-user-config.json`: gallery-dl configuration file for user-provided configuration (mostly meant for setting usernames and passwords), see the [gallery-dl documentation](https://github.com/mikf/gallery-dl/blob/master/docs/configuration.rst) for available options
* `hydownloader-config.json`: hydownloader configuration file
* `hydownloader-import-jobs.json`: configuration file for `hydownloader-importer` containing the rules for generating metadata for downloaded files

Besides running `hydownloader-daemon`, you should check out `hydownloader-tools`. You can use it to:

* Acquire pixiv login session data (username/password auth does NOT work for pixiv)
* Generate a report about errored/failing/dead/suspicious subscriptions and URL downloads to make identifying issues easier.
* Test downloading from specific sites. It is recommended to run
download tests regularly for sites you use. These check whether downloading actually works, the downloaded files and metadata are correct, etc.
Sometimes sites change and break the downloader. Although you will notice this also by checking the logs or URL/subscription statuses,
the tests can be run any time and without having to actually save files/metadata into your data folder. If something is broken, it will also
leave the test environment untouched so you can investigate the error.
* Mass add subscriptions and URLs to download.

## Site support

| Site | Anchor exporter | Subscriptions, single URL downloads | Test |
| ---- | --------------- | ----------------------------------- | ---- |
| pixiv | yes | yes | yes |
| gelbooru | yes | yes | yes |
| danbooru | yes | yes | yes |
| lolibooru.moe | yes | yes | yes |
| 3dbooru | yes | yes | yes |
| artstation | yes | yes | yes |
| sankaku | yes | yes | yes |
| idolcomplex | yes | yes | yes |
| twitter | yes | yes | yes |
| deviantart | yes | yes | yes |
| patreon | no | yes | yes |
| nijie | yes | yes | yes |
| tumblr | yes | yes | no |
| fantia | no | yes | no |
| fanbox | no | yes | no |
| webtoons | no | yes | yes |
| kemono.party | no | yes | no |
| coomer.party | no | yes | no |
| seiso.party | no | yes | no |
| baraag | no | yes | yes |
| pawoo | no | yes | yes |
| hentaifoundry | yes | yes | yes |
| yande.re | yes | yes | yes |
| rule34.xxx | yes | yes | yes |
| e621.net | yes | yes | yes |
| furaffinity.net | yes | yes | yes |
| instagram.com | no | yes | yes |
| any other site that gallery-dl supports | no | mostly* | no |

*Downloading works, automatically getting subscription info from URLs and checking file download status through API from the anchor database does not.

## Multithreaded downloading

This is an advanced topic. Unless you are scraping entire sites, it is likely that a single instance of hydownloader will be sufficient.
If you think otherwise, read on.

hydownloader does not natively support multiple URL or subscription downloads in parallel.
Due to technical difficulties (handling logs, cache, temporary files, database locking, etc.) this feature would be better implemented in gallery-dl itself.
However, gallery-dl currently also does not support this feature so it is not possible for hydownloader to rely on this.

A workaround is running multiple instances of hydownloader with separate databases.
In order to avoid downloading the same data multiple times on different instances, you can use the `gallery-dl.archive-override` configuration key
in `hydownloader-config.json`. In all the secondary instances, set this to the absolute filepath of the `anchor.db` of your primary instance.
Similarly, in the secondary instances, set `gallery-dl.data-override` to the path of the `data` folder of your primary instance.
With these option properly set, no duplicate files will be downloaded, no matter how many instances you run at the same time.
If you also want to have a common database of known downloaded URLs (e.g. for querying whether you already downloaded some URL or not in any of your instances),
then you can set the `shared-db-override` configuration key in all the secondary instances to the filepath of your main instance's `hydownloader.shared.db`.

Note that the secondary instances will still have separate databases, logs, configuration files, cookies and session data.
This means that for sites that need login, you will have to set it up for each instance separately (however, this also allows for downloading
from multiple different at the same time) and if you use custom configuration, you will have to apply it to each instance.

## Privacy notice

hydownloader contains absolutely no telemetry, analytics, remote logging, usage statistics, install ping or any other kind of spyware.
All network usage is according to the user configuration (subscriptions and URLs queued for download).
All logs, downloaded data and configuration is stored in the database folder. hydownloader does not read or write outside its database folder,
unless requested explicitly by some user-initiated command.

## Extending hydownloader

Pull requests are welcome.

### Adding support for sites that gallery-dl can already handle

First, decide what hydownloader-only features you want to support:

* Subscriptions: to make hydownloader able to recognize URL patterns for a site and extract subscription data / generate gallery URLs. You need to
add URL regex patterns for your site in `urls.py` for this.
* Anchor exporter / recognizing downloaded files from URLs: you need to add URL regex patterns in `urls.py`, expand `anchor_exporter.py` and
likely update the default gallery-dl configuration in `config.py` to make gallery-dl use a suitable anchor pattern for your site.
For all of these, try following how it is done for the already supported sites. Also familiarize yourself with the gallery-dl documentation, especially
the parts about the archive (anchor) and filename patterns.
* Tests (checking if downloading from a site works OK): look in `tools.py`. There are already tests for several sites, try to create yours based on those examples.

It is strongly recommended that if you add support for a site to hydownloader, you also add a download test for the site (the last item in the previous list).

### Adding support for sites that gallery-dl cannot currently handle

The hydownloader-specific modifications are the same as above, but first you need to write a downloader for gallery-dl (downloaders are called "extractors" in gallery-dl,
but the basic concept is the same.) gallery-dl is also written in Python like hydownloader, so Python knowledge is required.

It is preferable to try to get your downloader into gallery-dl upstream, but failing this, you can always run your own patched version of gallery-dl.

### Extending the program in some other way

Here is a quick table of contents for the source code:

* `db.py`: reading/writing `hydownloader.db`.
* `daemon.py`: the main `hydownloader-daemon` script. The API is defined here as is the code that checks for subscriptions/URLs and controls gallery-dl.
* `tools.py`: the `hydownloader-tools` script. Utilities that do not require a running `hydownloader-daemon` (e.g. statistics, reporting, some advanced database operations) go here.
* `urls.py`: URL patterns for extracing subscription data and anchors from URLs (regex). Also generating gallery URLs for subscriptions.
* `log.py`: Logging utility functions.
* `constants.py`: SQL commands to create the hydownloader database, default contents of configuration files are stored here.
* `importer.py`: the `hydownloader-importer` tool.
* `anchor_exporter.py`: the `hydownloader-anchor-exporter` tool.
* `gallery_dl_utils.py`: helper functions that directly interface with gallery-dl go here.
* `uri_normalizer.py`: URL normalizer, this is 3rd party code, do not touch without good reason.

## Planned features

* When using the API, "run_tests" and other long lasting actions should run in a separate worker thread
* Downloader for pixiv sketch (in gallery-dl)
* Check for and handle files already deleted from Hydrus in the importer (will need Hydrus API extension for force importing, and also for the forced re-import of existing non-deleted files)
* Save metadata files into an exportable database

## License

hydownloader is licensed under the Affero General Public License v3+ (AGPLv3+).
