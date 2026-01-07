"""
bcfeed proxy to fetch Bandcamp release metadata and embed URLs to avoid CORS in the browser.

Run locally:
    python embed_proxy.py

Then configure the dashboard to use the proxy, e.g. embed_proxy_url="http://localhost:5000/embed-meta".
"""

from __future__ import annotations

import ast
import datetime
import json
import os
import re
import threading
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, Response, stream_with_context, send_file
from queue import SimpleQueue
from werkzeug.serving import make_server, WSGIRequestHandler

from util import get_data_dir
from session_store import scrape_status_for_range, get_full_release_cache
from pipeline import gather_releases_with_cache
from gmail import _find_credentials_file, GmailAuthError, gmail_authenticate

app = Flask(__name__)

DATA_DIR = get_data_dir()
VIEWED_PATH = DATA_DIR / "viewed_state.json"
STARRED_PATH = DATA_DIR / "starred_state.json"
RELEASE_CACHE_PATH = DATA_DIR / "release_cache.json"
EMPTY_DATES_PATH = DATA_DIR / "no_results_dates.json"
SCRAPE_STATUS_PATH = DATA_DIR / "scrape_status.json"
EMBED_CACHE_PATH = DATA_DIR / "embed_cache.json"
TOKEN_PATH = DATA_DIR / "token.pickle"
CREDENTIALS_PATH = DATA_DIR / "credentials.json"
DASHBOARD_PATH = Path(__file__).resolve().with_name("dashboard.html")
POPULATE_LOCK = threading.Lock()


def _load_embed_cache() -> dict:
    if not EMBED_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(EMBED_CACHE_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _save_embed_cache(cache: dict) -> None:
    EMBED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = EMBED_CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    tmp.replace(EMBED_CACHE_PATH)


def _persist_embed_meta(url: str, *, release_id=None, is_track=None, embed_url=None, description=None) -> None:
    if not url:
        return
    cache = _load_embed_cache()
    existing = cache.get(url, {}) if isinstance(cache, dict) else {}
    merged = {
        "release_id": existing.get("release_id"),
        "is_track": existing.get("is_track"),
        "embed_url": existing.get("embed_url"),
        "description": existing.get("description"),
    }
    if release_id is not None:
        merged["release_id"] = release_id
    if is_track is not None:
        merged["is_track"] = is_track
    if embed_url is not None:
        merged["embed_url"] = embed_url
    if description is not None:
        merged["description"] = description
    cache[url] = merged
    _save_embed_cache(cache)


def _load_viewed() -> set[str]:
    if not VIEWED_PATH.exists():
        return set()
    try:
        data = json.loads(VIEWED_PATH.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()


def _save_viewed(items: set[str]) -> None:
    tmp = VIEWED_PATH.with_suffix(".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(sorted(items)), encoding="utf-8")
    try:
        tmp.replace(VIEWED_PATH)
    except FileNotFoundError:
        # If the temp file vanished between write and replace, fall back to writing directly.
        VIEWED_PATH.write_text(json.dumps(sorted(items)), encoding="utf-8")


def _load_starred() -> set[str]:
    if not STARRED_PATH.exists():
        return set()
    try:
        data = json.loads(STARRED_PATH.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()


def _save_starred(items: set[str]) -> None:
    tmp = STARRED_PATH.with_suffix(".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(sorted(items)), encoding="utf-8")
    try:
        tmp.replace(STARRED_PATH)
    except FileNotFoundError:
        STARRED_PATH.write_text(json.dumps(sorted(items)), encoding="utf-8")


def _extract_description(html_text: str) -> str | None:
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

        meta = soup.find("meta", attrs={"property": "og:description"}) or soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()
    except Exception:
        return None
    return None


def _parse_date(val: str) -> datetime.date | None:
    try:
        return datetime.datetime.strptime(val, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.datetime.strptime(val, "%Y/%m/%d").date()
        except Exception:
            return None


def _corsify(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    return False


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    return _corsify(jsonify({"ok": True}))

# Suppress noisy logging for health checks
class QuietHealthHandler(WSGIRequestHandler):
    def log_request(self, code="-", size="-"):
        if getattr(self, "path", "") == "/health":
            return
        super().log_request(code, size)


def start_proxy_server(port: int = 5050):
    """Start the proxy in a background thread and return (server, thread)."""
    server = make_server("0.0.0.0", port, app, threaded=True, request_handler=QuietHealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


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


def build_embed_url(item_id: Optional[int], is_track: bool) -> Optional[str]:
    if not item_id:
        return None
    kind = "track" if is_track else "album"
    base = "https://bandcamp.com/EmbeddedPlayer"
    return f"{base}/{kind}={item_id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/artwork=small/transparent=true/"


@app.route("/viewed-state", methods=["GET", "POST", "OPTIONS"])
def viewed_state():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    if request.method == "GET":
        items = sorted(_load_viewed())
        return _corsify(jsonify({"viewed": items}))

    data = request.get_json(silent=True) or {}
    url = data.get("url")
    read = data.get("read")
    if not url or not isinstance(read, bool):
        return _corsify(jsonify({"error": "Missing url or read flag"})), 400
    items = _load_viewed()
    if read:
        items.add(url)
    else:
        items.discard(url)
    _save_viewed(items)
    return _corsify(jsonify({"ok": True}))


@app.route("/releases", methods=["GET", "OPTIONS"])
def releases_endpoint():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    try:
        releases = get_full_release_cache()
        embed_cache = _load_embed_cache()
        if isinstance(embed_cache, dict) and embed_cache:
            for rel in releases:
                url = rel.get("url")
                meta = embed_cache.get(url or "")
                if not meta:
                    continue
                if meta.get("embed_url"):
                    rel["embed_url"] = meta.get("embed_url")
                if meta.get("release_id"):
                    rel["release_id"] = meta.get("release_id")
                if "is_track" in meta:
                    rel["is_track"] = meta.get("is_track")
                if meta.get("description"):
                    rel["description"] = meta.get("description")
    except Exception as exc:
        return _corsify(jsonify({"error": f"Failed to load releases: {exc}"})), 500
    return _corsify(jsonify({"releases": releases}))


@app.route("/starred-state", methods=["GET", "POST", "OPTIONS"])
def starred_state():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    if request.method == "GET":
        items = sorted(_load_starred())
        return _corsify(jsonify({"starred": items}))

    data = request.get_json(silent=True) or {}
    url = data.get("url")
    starred = data.get("starred")
    if not url or not isinstance(starred, bool):
        return _corsify(jsonify({"error": "Missing url or starred flag"})), 400
    items = _load_starred()
    if starred:
        items.add(url)
    else:
        items.discard(url)
    _save_starred(items)
    return _corsify(jsonify({"ok": True}))


@app.route("/config.json", methods=["GET"])
def config_json():
    embed_proxy_url = request.host_url.rstrip("/") + "/embed-meta"
    payload = {
        "title": "bcfeed",
        "embed_proxy_url": embed_proxy_url,
        "default_theme": "light",
        "clear_status_on_load": False,
        "show_dev_settings": False,
    }
    return _corsify(jsonify(payload))


@app.route("/dashboard", methods=["GET"])
def dashboard_page():
    if not DASHBOARD_PATH.exists():
        return _corsify(jsonify({"error": f"dashboard not found at {DASHBOARD_PATH}"})), 500
    return send_file(DASHBOARD_PATH, mimetype="text/html")


@app.route("/embed-meta", methods=["GET", "OPTIONS"])
def embed_meta():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    release_url = request.args.get("url")
    if not release_url:
        return _corsify(jsonify({"error": "Missing url parameter"})), 400
    try:
        resp = requests.get(
            release_url,
            headers={"User-Agent": "bcfeed/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        return _corsify(jsonify({"error": f"Failed to fetch Bandcamp page: {exc}"})), 502

    html_text = resp.text
    data = extract_bc_meta(html_text)
    description = _extract_description(html_text)
    if not data:
        return _corsify(jsonify({"error": "Unable to find bc-page-properties meta"})), 404

    item_id = data.get("item_id")
    is_track = data.get("item_type") == "track"
    embed_url = build_embed_url(item_id, is_track)

    # Persist embed metadata for future sessions.
    _persist_embed_meta(release_url, release_id=item_id, is_track=is_track, embed_url=embed_url, description=description)

    response = jsonify(
        {"release_id": item_id, "is_track": is_track, "embed_url": embed_url, "description": description}
    )
    return _corsify(response)


@app.route("/scrape-status", methods=["GET", "OPTIONS"])
def scrape_status():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    start_arg = request.args.get("start")
    end_arg = request.args.get("end")
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=60)
    start = _parse_date(start_arg) if start_arg else default_start
    end = _parse_date(end_arg) if end_arg else today
    if not start or not end or start > end:
        return _corsify(jsonify({"error": "Invalid start/end date"})), 400

    status = scrape_status_for_range(start, end)
    scraped = [day for day, is_scraped in status.items() if is_scraped]
    not_scraped = [day for day, is_scraped in status.items() if not is_scraped]
    return _corsify(jsonify({"scraped": scraped, "not_scraped": not_scraped}))


@app.route("/reset-caches", methods=["POST", "OPTIONS"])
def reset_caches():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    data = request.get_json(silent=True) or {}
    clear_cache = bool(data.get("clear_cache", False))
    clear_viewed = bool(data.get("clear_viewed", False))
    clear_starred = bool(data.get("clear_starred", False))

    cleared = []
    errors = []

    def _safe_unlink(path: Path):
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        return False

    if clear_cache:
        for p in (RELEASE_CACHE_PATH, EMPTY_DATES_PATH, SCRAPE_STATUS_PATH, EMBED_CACHE_PATH):
            if _safe_unlink(p):
                cleared.append(p.name)
    if clear_viewed or clear_starred:
        if _safe_unlink(VIEWED_PATH):
            cleared.append(VIEWED_PATH.name)
        if _safe_unlink(STARRED_PATH):
            cleared.append(STARRED_PATH.name)

    return _corsify(jsonify({"ok": True, "cleared": cleared, "errors": errors}))


@app.route("/populate-range", methods=["POST", "OPTIONS"])
def populate_range():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    data = request.get_json(silent=True) or {}
    start_raw = data.get("start") or data.get("from")
    end_raw = data.get("end") or start_raw
    max_results = int(data.get("max_results") or 2000)
    preload_embeds = _as_bool(data.get("preload_embeds"))
    if not start_raw or not end_raw:
        return _corsify(jsonify({"error": "Missing start/end"})), 400
    start = _parse_date(start_raw)
    end = _parse_date(end_raw)
    if not start or not end or start > end:
        return _corsify(jsonify({"error": "Invalid start/end date"})), 400

    if not _find_credentials_file():
        return _corsify(jsonify({"error": "Credentials not found. Reload credentials in the settings panel."})), 400
    if not TOKEN_PATH.exists():
        return _corsify(jsonify({"error": "Gmail token missing. Reload credentials in the settings panel to re-authenticate."})), 400

    if not POPULATE_LOCK.acquire(blocking=False):
        return _corsify(jsonify({"error": "Another populate is already running"})), 409
    logs = []

    def log(msg: str):
        logs.append(str(msg))

    try:
        gather_releases_with_cache(
            start.strftime("%Y/%m/%d"),
            end.strftime("%Y/%m/%d"),
            max_results,
            batch_size=20,
            log=log,
        )
        releases = get_full_release_cache()
        return _corsify(jsonify({"ok": True, "logs": logs, "count": len(releases)}))
    except GmailAuthError as exc:
        return _corsify(jsonify({"error": str(exc), "logs": logs})), 401
    except Exception as exc:
        return _corsify(jsonify({"error": str(exc), "logs": logs})), 500
    finally:
        POPULATE_LOCK.release()


@app.route("/clear-credentials", methods=["POST", "OPTIONS"])
def clear_credentials():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    logs: list[str] = []

    def log(msg: str):
        logs.append(str(msg))
        app.logger.info(msg)

    try:
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()
            log("Removed saved Gmail token.")
        log("Credentials cleared.")
        return _corsify(jsonify({"ok": True, "logs": logs}))
    except Exception as exc:
        log(f"ERROR: {exc}")
        return _corsify(jsonify({"error": str(exc), "logs": logs})), 500


@app.route("/load-credentials", methods=["POST", "OPTIONS"])
def load_credentials():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    logs: list[str] = []

    def log(msg: str):
        logs.append(str(msg))
        app.logger.info(msg)

    try:
        if "file" not in request.files:
            return _corsify(jsonify({"error": "No file uploaded"})), 400
        file = request.files["file"]
        if not file.filename:
            return _corsify(jsonify({"error": "Empty filename"})), 400
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CREDENTIALS_PATH.with_suffix(".tmp")
        file.save(tmp)
        tmp.replace(CREDENTIALS_PATH)
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()
            log("Removed existing Gmail token.")
        log("Saved credentials file. Authenticating…")
        gmail_authenticate()
        log("Credentials uploaded and authenticated.")
        return _corsify(jsonify({"ok": True, "logs": logs}))
    except Exception as exc:
        log(f"ERROR: {exc}")
        return _corsify(jsonify({"error": str(exc), "logs": logs})), 500


@app.route("/populate-range-stream", methods=["GET", "OPTIONS"])
def populate_range_stream():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    start_arg = request.args.get("start") or request.args.get("from")
    end_arg = request.args.get("end") or start_arg
    max_results = int(request.args.get("max_results") or 2000)
    preload_embeds = _as_bool(request.args.get("preload_embeds"))
    def error_stream(msg: str):
        def gen():
            yield f"event: error\ndata: {msg}\n\n"
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
        }
        # Also emit a one-line log-friendly version for browser status box
        app.logger.error(msg)
        return Response(stream_with_context(gen()), mimetype="text/event-stream", headers=headers)

    if not start_arg or not end_arg:
        return error_stream("Missing start/end")
    start = _parse_date(start_arg)
    end = _parse_date(end_arg)
    if not start or not end or start > end:
        return error_stream("Invalid start/end")
    if not _find_credentials_file():
        return error_stream("Credentials not found. Reload credentials in the settings panel.")
    if not TOKEN_PATH.exists():
        return error_stream("Gmail token missing. Reload credentials in the settings panel to re-authenticate.")

    if not POPULATE_LOCK.acquire(blocking=False):
        return error_stream("Another populate is already running")

    embed_proxy_url = request.host_url.rstrip("/") + "/embed-meta"

    def event_stream():
        q: SimpleQueue[str | None] = SimpleQueue()

        def log(msg: str):
            q.put(str(msg))

        def worker():
            try:
                gather_releases_with_cache(
                    start.strftime("%Y/%m/%d"),
                    end.strftime("%Y/%m/%d"),
                    max_results,
                    batch_size=20,
                    log=log,
                )
                q.put("Populate completed.")
            except GmailAuthError as exc:
                q.put(f"ERROR: {exc}")
            finally:
                q.put(None)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        try:
            while True:
                item = q.get()
                if item is None:
                    break
                safe = str(item).replace("\n", " ")
                yield f"data: {safe}\n\n"
            yield "event: done\ndata: complete\n\n"
        finally:
            POPULATE_LOCK.release()

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache",
    }
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream", headers=headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, threaded=True)
