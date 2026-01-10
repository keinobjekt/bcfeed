from __future__ import annotations

import ast
import json
import re
from typing import Optional

from bs4 import BeautifulSoup


def extract_bc_meta(html_text: str) -> Optional[dict]:
    soup = BeautifulSoup(html_text, "html.parser")
    meta = soup.find("meta", attrs={"name": "bc-page-properties"})
    if not meta or "content" not in meta.attrs:
        return None
    raw = meta["content"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return ast.literal_eval(raw)


def extract_bandcamp_description(html_text: str) -> str | None:
    if not html_text:
        return None
    try:
        soup = BeautifulSoup(html_text, "html.parser")

        def _collect(el):
            if not el:
                return ""
            text = el.get_text("\n")
            text = text.replace("\r\n", "\n")
            lines = [ln.strip() for ln in text.split("\n")]
            text = "\n".join(lines)
            return re.sub(r"\n{3,}", "\n\n", text).strip("\n")

        about = soup.find(id="tralbum-about") or soup.find("div", class_="tralbum-about")
        credits = soup.find(class_="tralbum-credits") or soup.find(id="tralbum-credits")

        parts = []
        about_text = _collect(about)
        credits_text = _collect(credits)
        if about_text:
            parts.append(about_text)
        if credits_text:
            parts.append(f"{credits_text}")
        if parts:
            return "\n\n".join(parts)

        meta = soup.find("meta", attrs={"property": "og:description"}) or soup.find(
            "meta", attrs={"name": "description"}
        )
        if meta and meta.get("content"):
            return meta["content"].strip()
    except Exception:
        return None
    return None


def build_embed_url(item_id: Optional[int], is_track: bool) -> Optional[str]:
    if not item_id:
        return None
    kind = "track" if is_track else "album"
    base = "https://bandcamp.com/EmbeddedPlayer"
    return f"{base}/{kind}={item_id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/artwork=small/transparent=true/"
