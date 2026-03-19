# bcfeed

A macOS desktop app that reads Bandcamp release emails from your email account, caches them locally, and generates an interactive dashboard of releases that is much easier to browse.

## Installation

### For power users (Homebrew already installed)

To install, open a Terminal and type the following:
`brew tap keinobjekt/bcfeed`
`brew install bcfeed`

Then to run simply type:
`bcfeed`

This will launch the server from the Terminal and open the dashboard in your web browser. You must keep the Terminal window open in the background in order to use **bcfeed**.


### For beginners

1) Download and install **Homebrew**: https://brew.sh
2) Use Homebrew to install **bcfeed**:
   - Open a Terminal window.
   - Type `brew tap keinobjekt/bcfeed` and hit enter.
   - Type `brew install bcfeed` and hit enter. This will begin the installation. 

To run **bcfeed**:
   - Type `bcfeed` into Terminal and hit enter
   - This will launch the server from the Terminal and open the dashboard in your web browser. 

You only need to install **bcfeed** once. 
You must keep the Terminal window open in the background in order to use **bcfeed**.


### Running from Python source (developers and advanced users)

If you're familiar with Python and CLI tools, you can create a virtual environment, install the dependencies and run the script from the CLI:

- Download **bcfeed** source code
- Ensure Python 3.10 or newer is installed and selected as the local python version
- In the project directory, run `virtualenv .venv`
- Run `source .venv/bin/activate`
- Download dependencies: `pip install -r requirements.txt`
- Run `python3 bcfeed.py`

This will launch the server from the CLI and open the dashboard in your web browser.

You must keep the CLI process running in order to use **bcfeed**.

## Choose an email provider

Open **Settings → Email Configuration** after launching the app. **bcfeed** supports two provider types:

- **Gmail API (OAuth)**: recommended if your Bandcamp mail lives in Gmail and you do not mind creating your own Google Cloud OAuth client.
- **IMAP**: works with many providers, including Gmail, iCloud, Outlook, Fastmail, and other IMAP-compatible mailboxes.

Sensitive Gmail OAuth material, Gmail tokens, and IMAP passwords managed by **bcfeed** are stored in your system keychain. Non-secret provider settings are stored locally in the app data directory.

Provider-specific setup guides:
- Gmail API (OAuth): [GMAIL_SETUP.md](GMAIL_SETUP.md)
- IMAP: [IMAP_SETUP.md](IMAP_SETUP.md)
