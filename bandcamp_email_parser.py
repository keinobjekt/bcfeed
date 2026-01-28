from __future__ import annotations

import re

from bs4 import BeautifulSoup
from furl import furl


def parse_release_email(email_html: str | bytes | None, subject: str | None = None):
    """
    Parse a Bandcamp release-notification email into lightweight release info.

    Returns:
        (img_url, release_url, is_track, artist_name, release_title, page_name)
    """
    img_url = None
    release_url = None
    is_track = None
    artist_name = None
    release_title = None
    page_name = None

    s = email_html
    try:
        s = s.decode()  # type: ignore[union-attr]
    except Exception:
        s = "" if s is None else str(s)

    if not s or s.lower() == "none":
        return None, None, None, None, None, None

    # Only accept messages whose subject starts with the expected release prefix.
    if subject and not subject.lower().startswith("new release from"):
        return None, None, None, None, None, None

    soup = BeautifulSoup(s, "html.parser")

    def _find_bandcamp_release_url() -> str | None:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            parsed = furl(href)
            path = str(parsed.path).lower()
            # Accept custom domains as long as the path looks like a release page.
            if "/album/" in path or "/track/" in path:
                return parsed.remove(args=True, fragment=True).url
        return None

    release_url = _find_bandcamp_release_url()
    if release_url is None:
        return None, None, None, None, None, None

    # track (vs release) flag
    release_path = str(furl(release_url).path).lower()
    is_track = "/track/" in release_path

    # attempt to scrape artist/release/page from the email itself
    # formats:
    # "page_name just released release_title by artist_name, check it out here"
    # "artist_name just released release_title, check it out here"
    full_text = soup.get_text(" ", strip=True)
    # Remove the leading greeting which always starts with "Greetings <username>, "
    if full_text.lower().startswith("greetings "):
        # drop first sentence up to first comma
        if "," in full_text:
            full_text = full_text.split(",", 1)[1].strip()
    # Strip the trailing call-to-action
    full_text = re.split(r",\s*check it out here", full_text, flags=re.IGNORECASE)[0].strip()

    # Expecting one of:
    # 1) "<page_name> just released <release_title>"
    # 2) "<page_name> just released <release_title> by <artist_name>"
    # or with "just announced" instead of "just released"
    release_phrase = r"just\s+(?:released|announced)"
    release_match = re.search(release_phrase, full_text, flags=re.IGNORECASE)
    after = ""
    if release_match:
        before, after = re.split(release_phrase, full_text, maxsplit=1, flags=re.IGNORECASE)
        page_name = (page_name or before).strip() if before else page_name
        after = after.strip()

    italic_texts = []
    for tag in soup.find_all(["span", "i", "em"]):
        style = tag.get("style", "").lower()
        if tag.name in {"i", "em"} or "italic" in style:
            text = tag.get_text(" ", strip=True)
            if text:
                italic_texts.append(text)

    if italic_texts:
        if after:
            for text in italic_texts:
                if text in after:
                    release_title = text
                    break
        if not release_title:
            release_title = italic_texts[0]

    if after and release_title:
        m = re.search(re.escape(release_title) + r"\s+by\s+(.+)$", after, flags=re.IGNORECASE)
        if m:
            artist_name = artist_name or m.group(1).strip()

    return img_url, release_url, is_track, artist_name, release_title, page_name

