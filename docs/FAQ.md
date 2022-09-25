# FAQ

### I can't download from danbooru even though I've set my username and password in the configuration.

The gallery-dl configuration key is unfortunately named, actually you have to use an API key and NOT your normal login password.
You can get one on the danbooru website somewhere under your account settings.

### I have a subcription that had a large number of files to download on the initial check, but the initial check got interrupted. Now it does not see the older files that it still needs to download. How to make it download all the files it should have downloaded at the initial check?

Set the "abort after" value to a larger value than the overall amount of files for your subscription query. Then it won't stop until it has completely gone through all files for that query.
Don't forget to change it back later.

### What do I write in the "downloader" and "keywords" fields when adding subscriptions?

Use the "downloaders" command of hydownloader-tools to list available downloaders and their URL patterns.
