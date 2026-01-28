import pickle
import sys
import base64
import json
import quopri
from email.utils import parsedate_to_datetime
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from paths import get_data_dir, GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE


class GmailAuthError(Exception):
    """Raised when Gmail OAuth credentials are missing, expired, or revoked."""


def _clear_token() -> None:
    """Remove saved token file to force a new auth flow next run."""
    try:
        token_path = get_data_dir() / GMAIL_TOKEN_FILE
        if token_path.exists():
            token_path.unlink()
    except Exception:
        pass

def _find_credentials_file() -> Path | None:
    """
    Look for credentials file in writable data dir, bundled resources, or CWD.
    """
    data_dir = get_data_dir()
    candidates = [
        data_dir / GMAIL_CREDENTIALS_FILE,
    ]
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / GMAIL_CREDENTIALS_FILE)
    candidates.append(Path.cwd() / GMAIL_CREDENTIALS_FILE)
    for path in candidates:
        if path.exists():
            return path
    return None


# ------------------------------------------------------------------------ 
def get_html_from_message(msg):
    """
    Extracts and decodes the HTML part from a Gmail 'full' message.
    Always returns a proper Unicode string (or None).
    """
    def walk_parts(part):
        mime_type = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")

        # If this part is HTML, decode it
        if mime_type == "text/html" and data:
            # Base64-url decode
            decoded_bytes = base64.urlsafe_b64decode(data)

            # Some Gmail messages use quoted-printable encoding inside HTML
            try:
                decoded_bytes = quopri.decodestring(decoded_bytes)
            except:
                pass

            # Convert to Unicode
            return decoded_bytes.decode("utf-8", errors="replace")

        # Multipart → recursive search
        for p in part.get("parts", []):
            html = walk_parts(p)
            if html:
                return html

        return None

    return walk_parts(msg["payload"])

# ------------------------------------------------------------------------ 
def gmail_authenticate():
    SCOPES = ['https://mail.google.com/'] # Request all access (permission to read/send/receive emails, manage the inbox, and more)

    creds = None
    data_dir = get_data_dir()
    token_path = data_dir / GMAIL_TOKEN_FILE

    # the file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if token_path.exists():
        with open(token_path, "rb") as token:
            creds = pickle.load(token)
    # if there are no (valid) credentials availablle, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as exc:
                _clear_token()
                raise GmailAuthError("Gmail access was revoked or expired. Reload credentials in the settings panel to re-authorize.") from exc
            except Exception as exc:
                _clear_token()
                raise GmailAuthError(f"Gmail refresh failed: {exc}") from exc
        else:
            cred_file = _find_credentials_file()
            if not cred_file:
                raise FileNotFoundError(f"Could not find {GMAIL_CREDENTIALS_FILE}. Reload credentials file in the settings panel to regenerate it.")
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), SCOPES)
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
    try:
        return build('gmail', 'v1', credentials=creds)
    except HttpError as exc:
        _clear_token()
        raise GmailAuthError("Gmail access failed; please reauthorize.") from exc

# ------------------------------------------------------------------------ 
def search_messages(service, query):
    try:
        result = service.users().messages().list(userId='me',q=query).execute()
        messages = [ ]
        if 'messages' in result:
            messages.extend(result['messages'])
        while 'nextPageToken' in result:
            page_token = result['nextPageToken']
            result = service.users().messages().list(userId='me',q=query, pageToken=page_token).execute()
            if 'messages' in result:
                messages.extend(result['messages'])
        return messages
    except Exception as exc:
        if type(exc) == HttpError:
            if getattr(exc, "status_code", None) == 401 or (exc.resp and exc.resp.status == 401):
                _clear_token()
                raise GmailAuthError("Gmail access revoked. Re-load the credentials in the settings and re-authorize.") from exc
        elif type(exc) == RefreshError:
            _clear_token()
            raise GmailAuthError("Gmail access revoked. Re-load the credentials in the settings and re-authorize.") from exc
        raise

# ------------------------------------------------------------------------ 
def get_messages(service, ids, format, batch_size, log=print):
    idx = 0
    emails = {}

    while idx < len(ids):
        if log:
            log(f'Downloading messages {idx} to {min(idx+batch_size, len(ids))}')
        batch = service.new_batch_http_request()
        for id in ids[idx:idx+batch_size]:
            batch.add(service.users().messages().get(userId = 'me', id = id, format=format))
        batch.execute()
        response_keys = [key for key in batch._responses]

        for key in response_keys:
            email_data = json.loads(batch._responses[key][1])
            if 'error' in email_data:
                err_msg = email_data['error']['message']
                if email_data['error']['code'] == 429:
                    raise Exception(f"{err_msg} Try reducing batch size using argument --batch.")
                elif email_data['error']['code'] == 401:
                    _clear_token()
                    raise GmailAuthError("Gmail access revoked; please reauthorize.")
                else:
                    raise Exception(err_msg)
            email = get_html_from_message(email_data)

            # Extract headers if available
            headers = email_data.get("payload", {}).get("headers", [])
            date_header = None
            subject_header = None
            for h in headers:
                name = h.get("name", "").lower()
                if name == "date":
                    date_header = h.get("value")
                if name == "subject":
                    subject_header = h.get("value")
            parsed_date = None
            if date_header:
                try:
                    parsed_date = parsedate_to_datetime(date_header).strftime("%Y-%m-%d")
                except Exception:
                    parsed_date = date_header

            emails[str(idx)] = {"html": email, "date": parsed_date, "subject": subject_header}
            idx += 1

    return emails
