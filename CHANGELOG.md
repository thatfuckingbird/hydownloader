# 0.21.0 (2022-06-05)

* Updated gallery-dl to 1.22.1
* Instagram support

# 0.20.0 (2022-05-26)

* Updated dependencies (including gallery-dl update to 1.22.0)
* Added the `--subdir` command line argument to hydownloader-importer
* Added support for coomer.party, Furaffinity and e621
* Some more pixiv direct file URLs are recognized now
* Default importer rules: update rules for newgrounds URLs
* Default importer rules: fix gelbooru ID tags and URLs
* Default gallery-dl configuration: Pixiv artist profile backgrounds and avatars are also downloaded now (in addition to artworks)

# 0.19.0 (2022-04-28)

* Added command to hydownloader-tools for downloading Pixiv user profile data
* Updated gallery-dl (1.21.2)

# 0.18.0 (2022-04-09)

* Updated gallery-dl (1.21.1), yt-dlp and other dependencies
* Twitter age-gate is now circumvented (thanks to gallery-dl)
* Importer: catch a previously uncaught error in URL validity checking
* Filename format for kemono.party was updated to avoid excessively long filenames causing errors
* Support added for rule34.xxx
* The default values for multiple configuration files changed this release. Make sure to read the update message in the log, and update your configuration files accordingly.

# 0.17.0 (2022-03-23)

* Importer now generates a "gallerydl_file_url" value if possible, so that importer configurations do not need to be modified due to the changes in 0.16.0
* Importer: fixed error when sorting files by ctime or mtime
* Fixed error on startup on Windows


# 0.16.0 (2022-03-14)

* Added subscription check time statistics to the report
* Started implementation of reverse lookup features (can't be used yet)
* The value of the "url-metadata" gallery-dl option is now managed by hydownloader (for most users this shouldn't matter, see the upgrade message in the log for details)
* Upgraded gallery-dl to 1.21.0
* Upgraded yt-dlp to latest version
* Some other minor dependency upgrades

# 0.15.0 (2022-02-17)

* Added option to disable WAL journaling

# 0.14.0 (2022-02-16)

* Dependency updates (most importantly gallery-dl to 1.20.5)
* gelbooru: recognize sample URL variants
* Fixed some failing site tests
* Fixed ffmpeg hang due to SIGTTOU on Linux

# 0.13.0 (2022-02-06)

* Dependency updates (most importantly gallery-dl to 1.20.4)

# 0.12.0 (2022-01-28)

* Dependency updates (most importantly gallery-dl to 1.20.2)

# 0.11.0 (2022-01-09)

* Dependency updates (most importantly gallery-dl to 1.20.1)

# 0.10.0 (2021-12-18)

* Updated hydrus-api module
* Further fixes to handling forward vs. backslashes in filepaths, including updates to the default importer job configuration
* Updated dependencies (including youtube-dlp and youtube-dl)
* Log files are now UTF-8 encoded, even on Windows (the daemon log will be automatically rotated because of this when you upgrade your db)
* Do not error in some specific circumstances if the anchor db hasn't been created yet
* Fix failing pixiv test in hydownloader-tools
* Added Python version display to the environment test in hydownloader-tools
* Importer: do not try to associate URLs if there are no URLs for a file
* Importer: added some datetime conversion helper functions
* Configuration files are now checked on startup for correct syntax
* Interrupting the process with Ctrl+C should now actually wait for the currently running downloads to finish
* Added /subscription_data_to_url API endpoint
* Extended the tracking of missed subscription checks, now all instances of potentially missed files can be identified just from checking this list
* Documentation updates, including documenting the 'missed subscription checks' feature

# 0.9.0 (2021-11-28)

* Update gallery-dl to 1.19.3
* Update yt-dlp and some other dependencies to their latest versions

# 0.8.0 (2021-11-23)

* (experimental) Add tracking of missed subscription checks (either due to hydownloader being interrupted or severely exceeding check interval)
* Update gallery-dl to 1.19.2
* The importer now uses forward slashes (/) for filepaths on all platforms. This is a breaking change and the importer configuration might need to be updated
* Removed Nuitka from dev dependencies

# 0.7.0 (2021-10-25)

* Switch from youtube-dl to yt-dlp, as youtube-dl seems abandoned
* Update gallery-dl to 1.19.1

# 0.6.0 (2021-10-08)

* Fix: URLs were converted to lowercase in some log messages (downloading was unaffected)
* Fix: crash due wrong encoding on Windows when reading gallery-dl output (now hydownloader sets PYTHONIOENCODING=utf-8)
* Fix: URLs containing colons (fuck you twitter)
* Fix: gallery-dl configuration for twitter direct image links

# 0.5.0 (2021-10-02)

* New command added to hydownloader-tools: rotate-daemon-log
* New options added to the report feature to include/exclude archived URLs and paused subscriptions
* Changed how the order of due subs is determined, priority is the primary ordering value now
* The `get_subscription_checks` API endpoint was changed to allow retrieving check history for multiple subs at once
* Updated gallery-dl to 1.19.0 (configuration file update required, see log for details)

# 0.4.0 (2021-09-11)

* Updated gallery-dl to 1.18.4
* Updated some other dependencies to newest versions
* Added `"fallback": false` for twitter in the default gallery-dl user configuration
* Added ability to set default values for subscription/single URL properties in `hydownloader-config.json`
