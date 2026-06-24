# IMAP setup guide

Use this guide for `Settings -> Email Configuration -> Provider -> IMAP`.

Only iCloud has been tested so far. If you confirm another provider works, or hit a provider-specific issue, open an issue at [github.com/keinobjekt/bcfeed/issues](https://github.com/keinobjekt/bcfeed/issues).

bcfeed IMAP supports standard username/password login only. Providers that require OAuth2 / Modern Auth for IMAP are unsupported.

1. Open `Settings`.
2. Set `Provider` to `IMAP`.
3. Enter the server, port, security mode, username, and password for your provider.
4. Click `Connect & load folders`.
5. Choose the folder that contains your Bandcamp emails, or use `Enter folder manually`.
6. Click `Save IMAP Configuration`.

<details>
<summary>iCloud Mail</summary>

| Field    | Details                                                                              |
| -------- | ------------------------------------------------------------------------------------ |
| Status   | Tested                                                                               |
| Server   | `imap.mail.me.com`                                                                   |
| Port     | `993`                                                                                |
| Security | `SSL/TLS`                                                                            |
| Username | The Apple ID email address you use to login to your account                          |
| Password | Apple app-specific password                                                          |

Two-factor authentication is required before Apple will let you create an app-specific password. If you reset your Apple Account password, Apple revokes existing app-specific passwords and you will need to generate a new one.

Docs: [server settings](https://support.apple.com/en-euro/102525), [app-specific passwords](https://support.apple.com/en-gu/102654)

</details>

<details>
<summary>Gmail</summary>

| Field    | Details             |
| -------- | ------------------- |
| Status   | Untested            |
| Server   | `imap.gmail.com`    |
| Port     | `993`               |
| Security | `SSL/TLS`           |
| Username | Full Gmail address  |
| Password | Google app password |

Google says IMAP is always on for personal Gmail now, so there is no personal-account IMAP toggle anymore. For Google Workspace accounts, Google no longer supports username/password access for third-party mail clients, so Gmail via bcfeed IMAP is unsupported there.

Docs: [Gmail in another client](https://support.google.com/mail/answer/7126229), [Google app passwords](https://support.google.com/accounts/answer/185833), [Workspace client setup](https://support.google.com/a/answer/9003945)

</details>

<details>
<summary>Yahoo Mail</summary>

| Field    | Details               |
| -------- | --------------------- |
| Status   | Untested              |
| Server   | `imap.mail.yahoo.com` |
| Port     | `993`                 |
| Security | `SSL/TLS`             |
| Username | Full Yahoo address    |
| Password | Yahoo app password    |

Yahoo requires an app password for third-party mail apps.

Docs: [Yahoo IMAP settings](https://help.yahoo.com/kb/yahoo-mail-imap-settings-sln4075.html), [Yahoo app passwords](https://help.yahoo.com/kb/account/confirm-delete-password-sln15241.html)

</details>

<details>
<summary>Fastmail</summary>

| Field    | Details                                  |
| -------- | ---------------------------------------- |
| Status   | Untested                                 |
| Server   | `imap.fastmail.com`                      |
| Port     | `993`                                    |
| Security | `SSL/TLS`                                |
| Username | Full Fastmail username, including domain |
| Password | Fastmail app password                    |

Fastmail says regular account passwords do not work for third-party mail clients. Basic plans also do not include IMAP access or app passwords.

Docs: [server names and ports](https://www.fastmail.help/hc/en-us/articles/1500000278342-Server-names-and-ports), [app passwords](https://www.fastmail.help/hc/en-us/articles/360058752854-App-passwords)

</details>

<details>
<summary>Outlook.com / Hotmail / Live</summary>

| Field    | Details                                    |
| -------- | ------------------------------------------ |
| Status   | Unsupported                                |
| Server   | `outlook.office365.com`                    |
| Port     | `993`                                      |
| Security | `SSL/TLS`                                  |
| Username | Full Microsoft email address               |
| Password | Microsoft account password or app password |

Microsoft documents Outlook.com IMAP with OAuth2 / Modern Auth. bcfeed IMAP only supports standard username/password login, so Outlook.com, Hotmail, and Live are unsupported here.

Docs: [Outlook.com IMAP settings](https://support.microsoft.com/en-gb/office/pop-imap-and-smtp-settings-for-outlook-com-d088b986-291d-42b8-9564-9c414e2aa040), [Microsoft app passwords](https://support.microsoft.com/en-gb/account-billing/how-to-get-and-use-app-passwords-5896ed9b-4263-e681-128a-a6f2979a7944)

</details>

If your provider is not listed, use its official IMAP docs to find the server name, port, security mode, username format, and whether it requires an app password.

## Troubleshooting

If login fails, double-check the server name, port, username, and security mode. If your provider uses two-factor authentication, you may need an app-specific password instead of your usual mailbox password.

If you can connect but cannot save, run `Connect & load folders` first, then choose a folder or enter one manually before saving.

If secure credential storage is unavailable, bcfeed cannot save IMAP passwords. Make sure your machine has a supported system keychain backend available.
