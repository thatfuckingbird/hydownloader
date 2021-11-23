# 0.8.0 (2021-11-07)

* (experimental) Added tracking of missed subscription checks (either due to hydownloader being interrupted or severely exceeding check interval)
*


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
