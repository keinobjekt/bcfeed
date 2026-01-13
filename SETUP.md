# bcfeed

A macOS desktop app that reads Bandcamp release emails from your Gmail, caches them locally, and generates an interactive dashboard of releases that is much easier to browse.


## Python setup (for power users)

If you're familiar with Python and CLI tools, simply create a virtual environment, install the dependencies and run the script from the CLI:

- Ensure Python 3.11 or newer is installed and selected as the local python version
- In the project directory, run `virtualenv .venv`
- Run `source .venv/bin/activate`
- Download dependencies: `pip install -r requirements.txt`
- Run `python3 bcfeed.py`


## Python setup (beginners' walkthrough)

1. Download and unzip the **bcfeed** source code into your Documents folder. Make sure the folder is called **bcfeed**.
2. Download and install **homebrew**: https://brew.sh/
3. Use Homebrew to install **Pyenv**. **Pyenv*** lets you easily select the right Python version:
  - Open a Terminal window and type `brew install pyenv`
4. Install Python 3.11:
  - In Terminal, type `pyenv install 3.11`
5. Tell Pyenv to use Python 3.11 for **bcfeed**:
  - In Terminal, navigate to the **bcfeed** directory: type `cd ~/Documents/bcfeed`
  - Type `pyenv local 3.11`
6. Install Virtualenv. This allows you to set up a virtual environment – an isolated directory containing all the packages bcfeed needs to run. 
  - Type `pip install virtualenv`
7. Create a virtual environment in the bcfeed folder.
  - Type `virtualenv .venv`
8. Activate the virtual environment you just created.
  - Type `source .venv/bin/activate`
9. Install the Python dependencies required by **bcfeed** to run.
  - Type `pip install -r requirements.txt`
10. You should now be ready to run **bcfeed**:
  - Type `python3 bcfeed.py`



## Running bcfeed

Once the Python setup has been completed you can run **bcfeed** with much fewer steps in future:

1. Open a Terminal window
2. Navigate to the **bcfeed** directory:
   `cd ~/Documents/bcfeed`
3. Activate the virtual environment:
   `source .venv/bin/activate`
4. Run the app:
   `python3 bcfeed.py`

This will launch the server app, which in turn will open the dashboard in your web browser.

You must keep the server app running in order to use **bcfeed**.


## 📘 Gmail Setup Guide

This application uses the Gmail API.
To keep your data private and avoid Google’s OAuth verification requirements, **you must create your own Google Cloud OAuth client**.
This setup is required only once and takes a few minutes.

---

### 1. Create a Google Cloud Project

1. Open: https://console.cloud.google.com/projectcreate  
2. Sign in with the Gmail account you use for Bandcamp.
3. Enter a project name: **bcfeed**
4. Click **Create**

---

### 2. Enable the Gmail API

1. Go to: https://console.cloud.google.com/apis/library/gmail.googleapis.com  
2. Click **Enable**

---

### 3. Configure the OAuth Consent Screen

1. Go to: https://console.cloud.google.com/auth/overview?project=bcfeed  
2. Click **Get Started** to configure Google Auth Platform
3. Fill in:
   - **App name:** bcfeed
   - **User support email:** your email  
   - Click **Next**.
4. Audience:
   - Select **External**.
   - Click **Next**.
5. Contact information – fill in:
   - **Email addresses:** your email again
   - Click **Next**.
6. Finish
   - Agree to the **Google API Services: User Data Policy**.
   - Click **Continue**.
7. Click **Create**.

---

### 4. Add Gmail read-only API scope

This allows the app to read your Gmail messages.

1. From the left-hand menu, click **Data Access**.
2. Click **Add or remove scopes**.
3. Scroll down to Manually Add Scopes, then paste the following URL:
   `https://www.googleapis.com/auth/gmail.readonly` (no quotes)
4. Click **Add to table**.
5. Click **Update** to exit the dialog.
6. At the bottom of the page, click **Save**.


---

### 5. Publish the App ("In Production")

Publishing allows Google to issue long-lived refresh tokens for your personal use.

1. On the left-hand menu, click **Audience**. 
2. Under Testing,click **Publish App**  
3. Confirm the dialog

You will see warnings that the app requires verification.
**This is normal and expected.**  
Since this OAuth client is used **only by you**, verification is **not required**.

---

### 6. Create OAuth Client Credentials (Desktop App)

1. Go to: https://console.cloud.google.com/apis/credentials  
2. Click **Create Credentials → OAuth client ID**  
3. Application type: **Desktop app**  
4. Click **Create**

Download the resulting JSON file, usually named:

`client_secret_XXXXXXXXX.json`

You will import this file into the application.

---

### 7. Use the Credentials in This Application

1. Open this application  
2. When prompted, select the downloaded `client_secret_XXXX.json` file  
3. When you click Run for the first time, a browser window will open asking you to sign in and approve access  
4. You may see a warning saying **Google hasn’t verified this app**. If so, click **Advanced** and then **Go to bcfeed (unsafe)**.
5. You will see a Google screen saying **bcfeed wants access to your Google Account**. Click **Continue**.
6. The app will store your refresh token locally so you will not need to log in again

---

## Important small print

- These credentials are **for your personal use only**. Do **not** share them.  
- The app is not a public OAuth client because **you** own and control the credentials.  
- Google allows unverified OAuth projects for personal/private use.  
- This setup avoids the verification and security audit required for public apps using restricted Gmail scopes.  
- You may revoke the app’s access at any time:  
  https://myaccount.google.com/permissions

---

## Troubleshooting

**I see an “unverified app” warning.**  
This is normal. Click **Continue**. The warning appears because only verified apps remove it, but personal-use apps do not require verification.

**The app says my token expired.**  
If you left your project in “Testing” mode, tokens expire after 7 days.  
Publishing the app to **In Production** fixes this.

**I get a 403 or insufficient permissions error.**  
Make sure you enabled the Gmail API and used the downloaded OAuth file.