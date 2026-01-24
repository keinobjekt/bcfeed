# bcfeed

**bcfeed** is a Python app that generates a dashboard of recent releases from Bandcamp pages you're subscribed to. It allows for a much more streamlined browsing experience than either the Bandcamp feed or going through your Gmail inbox.

It works by searching your Gmail inbox within a given date range for any "New release from..." emails from Bandcamp, then populating a *local* database of new releases. It then serves this database to a browser interface.

## Setup

See [SETUP.md]


## Typical workflow

Populating the database from you Gmail account is relatively fast – a few hundred releases should take a few seconds. However, loading the release details and player widget from the Bandcamp URL is much slower (a few seconds per release). Therefore, for a more enjoyable UX, it's generally recommended to pre-load releases before browsing.

You can either preload an entire date range – which is exhaustive but takes some time – or first "star" the releases you're interested in from the list (which preloads them under the hood) and *then* view the starred releases.

**A typical workflow would be:**

- **Select a date range to populate (e.g. the whole of last December)**. 
- **Click "Populate release list"**. This searches your Gmail inbox for Bandcamp release notifications within the specified date range and populates the database with their basic metadata (artist, title, bandcamp page, URL).
- Now you can either:
  - **Browse straight away** - this works, but releases may load slowly
or
  - **Click "Preload release data" and then browse** – this preloads the release text and BC player widget for all releases in the date range for faster browsing. May take a while for larger date ranges.
or
  - **"Star" the releases you're interested in, then browse the starred releases** - starring a release preloads it behind the scenes, and clicking "Show only: Starred" at the top right will filter starred releases for a given date range.
- Once you've browsed that date range, mark all the releases as "Seen" (in the left panel).


## Notes

- Once you've populated (or browsed) a date range from your inbox once, you don't have to do it again. Date ranges in the calendar widget correspond to the date the Bandcamp notification email was received.
- Releases with preloaded release data and player widgets are marked with a blue "CACHED" badge.
- The Settings panel at the top right allows you to reset the cache and load/clear your Gmail credentials.


## Requirements

- **bcfeed** has only been tested on OS X 13.4 and Chrome. It probably works on other OS X versions. It may or may not work on other browsers. It probably won't work on Windows, but feel free to try.

- You need a Gmail account – though IMAP support is in the works.


## Privacy

This application runs on your local machine. The application does not collect, transmit, store, or share your data with the author or any third party. All Gmail access is performed locally using OAuth credentials that you create and control in your own Google Cloud project. Gmail data retrieved by the application is processed only in memory or stored locally on your device, depending on your configuration. No analytics, telemetry, usage tracking, or remote logging is included; any Gmail data cached by the application remains entirely on your local machine.

The author of this software never has access to your OAuth credentials, access tokens, refresh tokens, or Gmail data.

You may revoke the application’s access to your Google account at any time via:
https://myaccount.google.com/permissions

This software is provided as-is for personal use. You are responsible for complying with Google’s API terms and policies when creating and using your own OAuth credentials.