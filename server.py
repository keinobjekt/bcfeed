"""
bcfeed local server that powers the dashboard, cache population, and embed metadata proxying.
"""

from __future__ import annotations

import datetime
import html
import json
import re
import socket
import threading
from pathlib import Path

import requests
from flask import Flask, jsonify, request, Response, stream_with_context, send_file
from queue import SimpleQueue
from werkzeug.serving import make_server, WSGIRequestHandler

from bandcamp import extract_bc_meta, extract_bandcamp_description, build_embed_url
from util import parse_date
from paths import (
    DATA_DIR,
    VIEWED_PATH,
    STARRED_PATH,
    RELEASE_CACHE_PATH,
    EMPTY_DATES_PATH,
    SCRAPE_STATUS_PATH,
    EMBED_CACHE_PATH,
    TOKEN_PATH,
    CREDENTIALS_PATH,
    DASHBOARD_PATH,
    DASHBOARD_CSS_PATH,
    DASHBOARD_JS_PATH,
    SETUP_PATH,
)
from session_store import scrape_status_for_range, get_full_release_cache
from pipeline import populate_release_cache, MaxResultsExceeded
from gmail import _find_credentials_file, GmailAuthError, gmail_authenticate

app = Flask(__name__)

POPULATE_LOCK = threading.Lock()
GMAIL_MAX_RESULTS_HARD = 2000


def _format_setup_inline(text: str) -> str:
    parts = text.split("`")
    out = []
    for idx, part in enumerate(parts):
        escaped = html.escape(part)
        if idx % 2 == 1:
            out.append(f"<code>{escaped}</code>")
        else:
            escaped = re.sub(
                r"(https?://[\\w\\-./?&#=%:+~]+)",
                r'<a href="\\1" target="_blank" rel="noopener">\\1</a>',
                escaped,
            )
            out.append(escaped)
    return "".join(out)


def _render_setup_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    out = []
    in_ul = False
    in_ol = False
    in_code = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for line in lines:
        stripped = line.rstrip()
        if stripped.strip().startswith("```"):
            if in_code:
                out.append("</code></pre>")
            else:
                close_lists()
                out.append("<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            out.append(html.escape(stripped))
            continue
        if not stripped.strip():
            close_lists()
            continue
        if stripped.strip() in {"---", "***", "___"}:
            close_lists()
            out.append("<hr />")
            continue
        heading = re.match(r"^(#{1,6})\\s+(.*)$", stripped)
        if heading:
            close_lists()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_format_setup_inline(heading.group(2))}</h{level}>")
            continue
        unordered = re.match(r"^\\s*[-*]\\s+(.*)$", stripped)
        if unordered:
            if not in_ul:
                close_lists()
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_format_setup_inline(unordered.group(1))}</li>")
            continue
        ordered = re.match(r"^\\s*\\d+\\.\\s+(.*)$", stripped)
        if ordered:
            if not in_ol:
                close_lists()
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{_format_setup_inline(ordered.group(1))}</li>")
            continue
        close_lists()
        out.append(f"<p>{_format_setup_inline(stripped)}</p>")

    close_lists()
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def _corsify(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _load_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()


def _save_set(path: Path, items: set[str]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(sorted(items)), encoding="utf-8")
    try:
        tmp.replace(path)
    except FileNotFoundError:
        # If the temp file vanished between write and replace, fall back to writing directly.
        path.write_text(json.dumps(sorted(items)), encoding="utf-8")


def _load_viewed() -> set[str]:
    return _load_set(VIEWED_PATH)


def _save_viewed(items: set[str]) -> None:
    _save_set(VIEWED_PATH, items)


def _load_starred() -> set[str]:
    return _load_set(STARRED_PATH)


def _save_starred(items: set[str]) -> None:
    _save_set(STARRED_PATH, items)


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


def _save_embed_metadata(url: str, *, release_id=None, is_track=None, embed_url=None, description=None) -> None:
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


def start_server(port: int = 5050):
    """Start the server in a background thread and return (server, thread)."""
    server = make_server("0.0.0.0", port, app, threaded=True, request_handler=QuietHealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def find_free_port(preferred: int = 5050) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("", preferred))
            return preferred
        except OSError:
            sock.bind(("", 0))
            return sock.getsockname()[1]


def start_server_thread(preferred_port: int = 5050):
    port = find_free_port(preferred_port)
    server, thread = start_server(port)
    return server, thread, port


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
        "has_token": TOKEN_PATH.exists(),
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


@app.route("/dashboard.css", methods=["GET"])
def dashboard_css():
    if not DASHBOARD_CSS_PATH.exists():
        return _corsify(jsonify({"error": f"dashboard css not found at {DASHBOARD_CSS_PATH}"})), 500
    return send_file(DASHBOARD_CSS_PATH, mimetype="text/css")


@app.route("/dashboard.js", methods=["GET"])
def dashboard_js():
    if not DASHBOARD_JS_PATH.exists():
        return _corsify(jsonify({"error": f"dashboard js not found at {DASHBOARD_JS_PATH}"})), 500
    return send_file(DASHBOARD_JS_PATH, mimetype="application/javascript")


@app.route("/setup", methods=["GET"])
def setup_doc():
    if not SETUP_PATH.exists():
        return _corsify(jsonify({"error": f"SETUP.md not found at {SETUP_PATH}"})), 500
    markdown_text = SETUP_PATH.read_text(encoding="utf-8")
    try:
        body = _render_setup_html(markdown_text)
    except Exception:
        body = f"<pre>{html.escape(markdown_text)}</pre>"
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>bcfeed setup</title>
  <style>
    :root {{
      color-scheme: light dark;
    }}
    body {{
      margin: 0;
      padding: 32px 18px 60px;
      font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
      background: #f7f8fb;
      color: #0a0f1a;
      line-height: 1.6;
    }}
    .wrap {{
      max-width: 900px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d9e2ef;
      border-radius: 12px;
      padding: 28px 28px 36px;
      box-shadow: 0 12px 30px rgba(0,0,0,0.08);
    }}
    h1, h2, h3, h4, h5, h6 {{
      margin: 18px 0 10px;
      line-height: 1.25;
    }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 22px; }}
    h3 {{ font-size: 18px; }}
    p {{ margin: 10px 0; }}
    ul, ol {{ margin: 8px 0 12px 20px; }}
    li {{ margin: 4px 0; }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      background: #f1f4f8;
      padding: 1px 4px;
      border-radius: 4px;
      font-size: 0.95em;
    }}
    pre {{
      background: #0f1116;
      color: #f4f6fb;
      padding: 12px 14px;
      border-radius: 8px;
      overflow-x: auto;
    }}
    pre code {{
      background: transparent;
      padding: 0;
      color: inherit;
    }}
    a {{ color: #1f7aff; }}
    hr {{
      border: none;
      border-top: 1px solid #e3e8f2;
      margin: 18px 0;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    {body}
  </div>
</body>
</html>"""
    return Response(doc, mimetype="text/html")


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
    description = extract_bandcamp_description(html_text)
    if not data:
        return _corsify(jsonify({"error": "Unable to find bc-page-properties meta"})), 404

    item_id = data.get("item_id")
    is_track = data.get("item_type") == "track"
    embed_url = build_embed_url(item_id, is_track)

    # Persist embed metadata for future sessions.
    _save_embed_metadata(release_url, release_id=item_id, is_track=is_track, embed_url=embed_url, description=description)

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
    start = parse_date(start_arg, allow_none=True) if start_arg else default_start
    end = parse_date(end_arg, allow_none=True) if end_arg else today
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
    max_results = int(request.args.get("max_results") or GMAIL_MAX_RESULTS_HARD)
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
    start = parse_date(start_arg, allow_none=True)
    end = parse_date(end_arg, allow_none=True)
    if not start or not end or start > end:
        return error_stream("Invalid start/end")
    if not _find_credentials_file():
        return error_stream("Credentials not found. Reload credentials in the settings panel.")
    if not TOKEN_PATH.exists():
        return error_stream("Gmail token missing. Reload credentials in the settings panel to re-authenticate.")

    if not POPULATE_LOCK.acquire(blocking=False):
        return error_stream("Another populate is already running")

    def event_stream():
        q: SimpleQueue[str | None] = SimpleQueue()

        def log(msg: str):
            q.put(str(msg))

        def worker():
            try:
                populate_release_cache(
                    start.strftime("%Y-%m-%d"),
                    end.strftime("%Y-%m-%d"),
                    max_results,
                    batch_size=20,
                    log=log,
                )
                q.put("Populate completed.")
            except GmailAuthError as exc:
                q.put(f"ERROR: {exc}")
            except MaxResultsExceeded as exc:
                q.put(f"Maximum results reached ({exc.found}/{exc.max_results}).")
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
