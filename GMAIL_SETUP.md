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

Keep this file safe – if you ever need to clear and re-load your credentials, you can skip all the steps above if you still have this file somewhere.

---

### 7. Use the Credentials in This Application

1. Open this application  
2. Open **Settings → Email Configuration**
3. Set **Provider** to **Gmail API (OAuth)**
4. Click **Load credentials file** and choose the downloaded `client_secret_XXXX.json` file
5. When prompted, continue with the Google sign-in flow in your browser
6. You may see a warning saying **Google hasn’t verified this app**. If so, click **Advanced** and then **Go to bcfeed (unsafe)**.
7. You will see a Google screen saying **bcfeed wants access to your Google Account**. Click **Continue**.
8. The imported OAuth client details and your Gmail token will be stored securely in your system keychain so you will not need to log in again

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

**The app says secure credential storage is unavailable.**
**bcfeed** stores imported Gmail OAuth material and Gmail tokens in the system keychain. Make sure your machine has a supported keychain backend available.
