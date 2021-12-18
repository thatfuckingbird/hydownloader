# hydownloader API documentation

## Accessing the API

All requests to the API must have the HyDownloader-Access-Key header.
Set it to the access key that is in your hydownloader configuration.
If the header is missing or the keys don't match you will get 403.

## API endpoints

All endpoints are POST. I don't care.

In the following, "entries" or "database entries" (e.g. "known URL entries", "subscription entries", etc.)
refer to database rows converted to JSON objects, with the column names as keys. Check the database schema to see what keys are available.
For example, if some endpoint takes or returns a list of "single URL queue entries", then these will be JSON objects corresponding
to rows in the single URL queue database table. When an endpoint takes such entries as inputs, then you do not usually have to
set a value for every column found in the database table as most have default values (again, check the schema).

### POST /api_version

Returns a JSON object with a `version` field containing the API version (an integer).

### POST /url_info

The request body must be a JSON object containing a list of URLs in the `urls` field.
The response is a JSON list of URL info objects.
Each object has the following keys:

| Key | Value |
|-----|-------|
| queue_info | a list of all single URL queue entries where the URL is the same as the input URL |
| anchor_info | true if there is an anchor in the database that matches the input URL, false otherwise |
| known_url_info | a list of all known URL entries that match the input URL |
| gallerydl_downloader | the name of the gallery-dl extractor that matches this URL, or an empty string if there is no match |
| sub_downloader | the name of the hydownloader subscription downloader that matches this URL, or an empty string if there is no match |
| sub_keywords | the subscription keywords string extracted from this URL if it matches a hydownloader subscription downloader, or an empty string if there is no match |
| existing_subscriptions | a list of hydownloader subscription entries that match this URL (have the same downloader and keywords as the ones extracted from this URL) |

### POST /subscription_data_to_url

The request body must be a JSON object containing the `downloader` and `keywords` string fields.
It returns an object with the `url` field containing a string with the gallery URL generated from the given downloader and keywords, or an empty string if no URL could be generated.

### POST /add_or_update_urls

The request body must be a JSON list of URL database entry objects. If an object does not have the "id" field, it will be treated as a new URL to add.
If it does have the "id" field, the URL entry with the same ID will be updated. New URLs must have the "url" field, updates must have the "id" field. Other than these, all fields are optional.
Returns a JSON object with a boolean "status" field.

### POST /delete_urls

The request body must be a JSON object with a field named "ids" which must be a list of (integer) URL ids.
Returns a JSON object with a boolean "status" field.

### POST /get_queued_urls

The request body is either empty (returns all URL entries), contains a list of IDs in the "ids" field,
or contains a minimal and maximal ID in the "from" and "to" fields.
It may optionally contain a boolean "archived" field to also return entries marked as archived (defaults to false).
The response is a JSON list of single URL queue entries.

### POST /add_or_update_subscriptions

Works the same as the corresponding endpoint for URLs.

### POST /get_subscriptions

Works the same as the corresponding endpoint for URLs.

### POST /delete_subscriptions

Works the same as the corresponding endpoint for URLs.

### POST /add_or_update_subscription_checks

Works the same as the corresponding endpoints for URLs and subscriptions, except that instead of "id",
the ID column is called "rowid".

### POST /get_subscription_checks

Works the same as the corresponding endpoints for URLs and subscriptions, except that instead of "id",
the ID column is called "rowid". The "from" and "to" keys fields are not supported.

### POST /add_or_update_missed_subscription_checks

Works the same as the corresponding endpoints for URLs and subscriptions, except that instead of "id",
the ID column is called "rowid".

### POST /get_missed_subscription_checks

Works the same as the corresponding endpoints for URLs and subscriptions, except that instead of "id",
the ID column is called "rowid". The "from" and "to" keys fields are not supported.

### POST /subscriptions_last_files

The request body must be a JSON object with a field called "ids" which must be a list of
subscription IDs.
Returns a JSON list of objects, where each object has a "paths" field containing the path
of the last 5 files downloaded from the corresponding subscription as a list (it can contain less than 5 or even be empty if there are no such files).

### POST /urls_last_files

Works the same as the corresponding endpoint for subscriptions.

### POST /get_status_info

Returns a JSON object with the following fields:
* subscriptions_due: number of due subscriptions
* urls_queued: number of queued URLs
* subscriptions_paused: boolean, true if the subscription worker is paused
* urls_paused: boolean, true if the URL queue worker is paused
* subscription_worker_status: human-readable status string for the subscription worker
* url_worker_status: human-readable status string for the URL worker
* subscription_worker_last_update_time: time of last status update for the subscription worker
* _url_worker_last_update_time: time of last status update for the URL queue worker

### POST /set_cookies

The request body must be a JSON object with a "cookies" field which is a list of
cookies. Each cookie is a list of exactly 5 values: name, value, domain, path, expiration (in this order).
Returns a JSON object with a boolean "status" field.

### POST /pause_subscriptions

Pauses the subscription worker. This endpoint is idempotent.
Returns a JSON object with a boolean "status" field.

### POST /resume_subscriptions

Resumes the subscription worker. This endpoint is idempotent.
Returns a JSON object with a boolean "status" field.

### POST /pause_single_urls

Pauses the URL worker. This endpoint is idempotent.
Returns a JSON object with a boolean "status" field.

### POST /resume_single_urls

Resumes the URL worker. This endpoint is idempotent.
Returns a JSON object with a boolean "status" field.

### POST /run_tests

The request body must be a JSON object with a "sites" field which
must be a list of test names (see the help for `hydownloader-tools` for the available values).
Returns a JSON object with a boolean "status" field.

### POST /run_report

The request body must be a JSON object with a boolean "verbose" field.
The generated report will be written to the daemon log (will not be returned).
Returns a JSON object with a boolean "status" field.

### POST /shutdown

Requests a clean shutdown (not immediate, finishes the currently running URL and subscription first).
Returns a JSON object with a boolean "status" field.

### POST /kill_current_url

Force aborts the currently running URL download (if there is any).
Returns a JSON object with a boolean "status" field.

### POST /kill_current_sub

Force aborts the currently running subscription check (if there is any).
Returns a JSON object with a boolean "status" field.

## Downloading files

You can download any file from the hydownloader root path by sending a GET request where the path is the same
as the path to file you want to download, relative to the hydownloader root path.
For example, `GET /logs/daemon.txt` will get you the main daemon log.
