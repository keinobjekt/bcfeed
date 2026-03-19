# bcfeed

## Introduction

**bcfeed** is a Python app that generates a dashboard of releases from your Bandcamp release notification emails. 

It works by searching your configured email account within a given date range for any "New release from..." emails from Bandcamp, then populating a local database of releases.

You can connect either:

- a Gmail account using the Gmail API and your own OAuth client
- any IMAP-compatible mailbox by entering the server details in the Settings panel


## Setup

See [SETUP.md](SETUP.md)


## Workflow

**A typical workflow would be:**

1) **Select a date range to populate**, e.g. the whole of last December. 
2) Click **"Populate release list"**. This searches your configured provider for Bandcamp release notifications within the specified date range and populates the database.
3) Now you can do one of three things:
  - **Browse straight away** - this works! However, this is likely to be slow – the data for each release needs to be loaded from each Bandcamp page individually, which takes a few seconds any time you click on a release. For a more enjoyable UX, you can
  - Click **"Preload release data"** and then browse: this preloads the release info and BC player widgets for all releases in the selected date range for faster browsing, but may take a while for larger date ranges. Or you can
  - **"Star" the releases you're interested in, then filter and browse the starred releases using the "Starred" button at the top right**. Starring a release triggers a preload behind the scenes, so by the time you click "Starred", the releases should already be loaded.
4) If you like, once you've browsed that date range, you can mark all the releases as "Seen" (in the left panel). 


## Notes

Once you've populated (or browsed) a date range from your mailbox once, you don't have to do it again. Each line in the database corresponds to an *email* in your inbox. So if you've already populated a date range in the past, that's all the releases (emails) you'll ever see in that date range.

Releases with preloaded release data and player widgets are marked with a blue "CACHED" badge.

The Settings panel at the top right allows you to choose a provider, load or clear Gmail credentials, configure IMAP host/user/folder settings, and reset the cache.

Sensitive Gmail OAuth material, Gmail tokens, and IMAP passwords managed by **bcfeed** are stored securely in your system keychain.


## Performance

### Why are releases loading so slowly?

Make sure to read the bit above about pre-loading releases.

Typically it's pretty quick to populate the database from Gmail, a few hundred emails should take a few seconds. IMAP accounts can take a bit longer and be provider dependant, though ~100 emails should typically not take much longer than a minute. However, Bandcamp release notification emails only contain basic metadata (artist, title, label/page, Bandcamp URL). Fetching the Bandcamp player widget and release info requires scraping the Bandcamp page for each release, which is much slower (a few seconds per release). Naturally, you are also at the mercy of the Bandcamp servers at any given moment – it's not uncommon for them to slow to a crawl.

In general it's better to pre-load the releases, either using the "Preload" button on the left side or by starring them.

The good news is that **bcfeed** caches the release database, release info and Bandcamp player widgets locally and these persist across **bcfeed** sessions, so you only need to preload once for any given release.


## Requirements

**bcfeed** has only been tested on OS X 13.4 and Chrome. It probably works on other OS X versions. It may or may not work on other browsers. It probably won't work on Windows, but feel free to try.

**bcfeed** supports:
- Gmail accounts via the Gmail API and your own OAuth client
- IMAP-compatible accounts via the Settings panel

Some IMAP providers require IMAP to be enabled and/or an app-specific password. Secure credential storage also requires a working system keychain backend (available by default on macOS).


## Privacy

This application runs on your local machine. The application does not collect, transmit, store, or share your data with the author or any third party. Gmail API access and IMAP access are performed locally using credentials that you create and control. Sensitive Gmail OAuth material, Gmail tokens, and IMAP passwords managed by **bcfeed** are stored securely in your system keychain. Email data retrieved by the application is processed only in memory or stored locally on your device, depending on your configuration. No analytics, telemetry, usage tracking, or remote logging is included; any cached email-derived data remains entirely on your local machine.

The author of this software never has access to your OAuth credentials, access tokens, refresh tokens, IMAP passwords, or email data.

If you use the Gmail provider, you may revoke the application’s access to your Google account at any time via:
https://myaccount.google.com/permissions

This software is provided as-is for personal use. You are responsible for complying with your email provider’s terms when creating and using OAuth credentials, IMAP passwords, or app-specific passwords.
