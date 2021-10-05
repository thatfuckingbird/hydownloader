# 0.6.0 (not yet released)

* Fix: URLs were converted to lowercase in some log messages (downloading was unaffected)
* Fix: crash due wrong encoding on Windows when reading gallery-dl output (now hydownloader set PYTHONIOENCODING=utf-8)

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
