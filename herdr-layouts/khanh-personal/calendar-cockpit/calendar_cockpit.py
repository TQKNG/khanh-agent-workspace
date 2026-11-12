"""Local Google Calendar hub for the Herdr meetings view.

This service intentionally implements only the small Cockpit protocol surface
needed by the existing Herdr meetings mod: hub start, subscribe, and view.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn, StreamRequestHandler, TCPServer


ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
DATA = ROOT / "data"
CREDENTIALS = ROOT / "credentials.json"
TOKEN = DATA / "token.json"
HUB_INFO = CACHE / "hub.json"
SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class CalendarError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_google_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    if len(value) == 10:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_time(value: datetime, all_day: bool) -> str:
    if all_day:
        return "All day"
    return value.astimezone().strftime("%I:%M %p").lstrip("0")


def format_day(value: date) -> str:
    return value.strftime("%A, %B %d").replace(" 0", " ")


def format_duration(start: datetime, end: datetime, all_day: bool) -> str:
    if all_day:
        return "all day"
    minutes = max(1, round((end - start).total_seconds() / 60))
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder}m" if hours else f"{remainder}m"


def short_duration(seconds: float) -> str:
    minutes = max(0, round(seconds / 60))
    if minutes < 1:
        return "<1m"
    if minutes < 60:
        return f"{minutes}m"
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder}m" if remainder else f"{hours}h"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise CalendarError(f"Invalid JSON in {path.name}: {exc}") from exc


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


class GoogleCalendar:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.cached: dict | None = None
        self.cached_at = 0.0

    def credentials(self) -> dict:
        value = load_json(CREDENTIALS)
        installed = value.get("installed") or value.get("web")
        if not installed:
            raise CalendarError(
                "Google OAuth is not configured. Download a Desktop app client JSON "
                "and save it as calendar-cockpit/credentials.json."
            )
        return installed

    def access_token(self) -> str:
        token = load_json(TOKEN)
        if token.get("access_token") and token.get("expires_at", 0) > time.time() + 60:
            return token["access_token"]
        if token.get("refresh_token"):
            return self.refresh(token, self.credentials())
        return self.authorize(self.credentials())

    def refresh(self, token: dict, client: dict) -> str:
        form = urllib.parse.urlencode(
            {
                "client_id": client["client_id"],
                "client_secret": client.get("client_secret", ""),
                "refresh_token": token["refresh_token"],
                "grant_type": "refresh_token",
            }
        ).encode()
        request = urllib.request.Request(GOOGLE_TOKEN_URL, data=form, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        response = self.urlopen(request)
        token.update(response)
        token["expires_at"] = time.time() + int(response.get("expires_in", 3600))
        save_json(TOKEN, token)
        return token["access_token"]

    def authorize(self, client: dict) -> str:
        callback: dict[str, str] = {}

        class Callback(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                callback["code"] = query.get("code", [""])[0]
                callback["error"] = query.get("error", [""])[0]
                body = "Google Calendar authorization received. You can close this window."
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *_args) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), Callback)
        port = server.server_address[1]
        redirect_uri = f"http://127.0.0.1:{port}/oauth2callback"
        params = urllib.parse.urlencode(
            {
                "client_id": client["client_id"],
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": SCOPE,
                "access_type": "offline",
                "prompt": "consent",
            }
        )
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
        print("Opening Google Calendar authorization in your browser...", flush=True)
        webbrowser.open(url)
        server.handle_request()
        server.server_close()
        if callback.get("error"):
            raise CalendarError(f"Google authorization failed: {callback['error']}")
        if not callback.get("code"):
            raise CalendarError("Google authorization returned no code")

        form = urllib.parse.urlencode(
            {
                "code": callback["code"],
                "client_id": client["client_id"],
                "client_secret": client.get("client_secret", ""),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode()
        request = urllib.request.Request(GOOGLE_TOKEN_URL, data=form, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        token = self.urlopen(request)
        token["expires_at"] = time.time() + int(token.get("expires_in", 3600))
        save_json(TOKEN, token)
        return token["access_token"]

    def urlopen(self, request: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise CalendarError(f"Google Calendar request failed ({exc.code}): {detail[:300]}") from exc
        except urllib.error.URLError as exc:
            raise CalendarError(f"Google Calendar is unreachable: {exc.reason}") from exc

    def events(self) -> list[dict]:
        now = utc_now()
        params = urllib.parse.urlencode(
            {
                "timeMin": rfc3339(now - timedelta(hours=1)),
                "timeMax": rfc3339(now + timedelta(days=7)),
                "singleEvents": "true",
                "orderBy": "startTime",
                "showDeleted": "false",
                "maxResults": "2500",
            }
        )
        request = urllib.request.Request(f"{GOOGLE_EVENTS_URL}?{params}")
        request.add_header("Authorization", f"Bearer {self.access_token()}")
        return self.urlopen(request).get("items", [])

    def model(self) -> dict:
        with self.lock:
            if self.cached is not None and time.time() - self.cached_at < 45:
                return self.cached
            model = build_model(self.events())
            self.cached = model
            self.cached_at = time.time()
            return model


def event_model(event: dict, now: datetime) -> dict | None:
    start_info = event.get("start", {})
    end_info = event.get("end", {})
    all_day = "date" in start_info
    start = parse_google_datetime(start_info.get("date") or start_info.get("dateTime"))
    end = parse_google_datetime(end_info.get("date") or end_info.get("dateTime"))
    if not start or not end:
        return None
    if all_day:
        end -= timedelta(seconds=1)
    state = "past" if end < now else "now" if start <= now <= end else "upcoming"
    if state == "upcoming" and (start - now).total_seconds() <= 15 * 60:
        state = "soon"
    attendees = event.get("attendees", [])
    self_attendee = next((a for a in attendees if a.get("self")), None)
    response = (self_attendee or {}).get("responseStatus", "needsAction")
    people = [a.get("displayName") or a.get("email") for a in attendees if a.get("email")][:12]
    conference = event.get("conferenceData", {}).get("entryPoints", [])
    join = next((p.get("uri") for p in conference if p.get("entryPointType") == "video" and p.get("uri")), None)
    event_id = event.get("id") or secrets.token_hex(8)
    local_start = start.astimezone()
    local_end = end.astimezone()
    acts = [{"id": "open", "label": "Open", "key": "o"}]
    if join:
        acts.insert(0, {"id": "join", "label": "Join", "key": "j", "main": True})
    return {
        "id": f"google:{event_id}",
        "title": event.get("summary") or "Untitled event",
        "day": local_start.date().isoformat(),
        "time": format_time(local_start, all_day),
        "duration": format_duration(start, end, all_day),
        "when": "All day" if all_day else f"{format_day(local_start.date())} at {format_time(local_start, False)}",
        "span": "All day" if all_day else f"{format_time(local_start, False)} - {format_time(local_end, False)}",
        "until": short_duration((start - now).total_seconds()) if start > now else short_duration((end - now).total_seconds()),
        "state": state,
        "response": response,
        "attendees": len(attendees),
        "people": people,
        "url": event.get("htmlLink"),
        "join": join,
        "acts": acts,
        "raw": {"google_id": event_id},
    }


def build_model(events: list[dict]) -> dict:
    now = datetime.now().astimezone()
    meetings = [m for e in events if (m := event_model(e, now))]
    meetings.sort(key=lambda m: (m["day"], m["time"], m["title"]))
    by_id = {m["id"]: m for m in meetings}
    today = now.date().isoformat()
    days: list[dict] = []
    for offset in range(8):
        current = now.date() + timedelta(days=offset)
        ids = [m["id"] for m in meetings if m["day"] == current.isoformat()]
        days.append({"date": current.isoformat(), "label": format_day(current), "today": offset == 0, "ids": ids})
    grid_days = [{"date": d["date"], "label": d["label"]} for d in days]
    blocks = []
    for m in meetings:
        if m["time"] == "All day":
            continue
        source = next((e for e in events if f"google:{e.get('id')}" == m["id"]), None)
        if not source:
            continue
        start = parse_google_datetime(source.get("start", {}).get("dateTime"))
        end = parse_google_datetime(source.get("end", {}).get("dateTime"))
        if not start or not end:
            continue
        local_start, local_end = start.astimezone(), end.astimezone()
        day_index = next((i for i, d in enumerate(days) if d["date"] == m["day"]), 0)
        blocks.append({"id": m["id"], "day": day_index, "top": local_start.hour + local_start.minute / 60, "bottom": local_end.hour + local_end.minute / 60})
    upcoming = next((m for m in meetings if m["state"] in {"now", "soon", "upcoming"}), None)
    banner = {"state": "none"}
    if upcoming:
        banner = {
            "state": upcoming["state"],
            "id": upcoming["id"],
            "title": upcoming["title"],
            "when": upcoming["when"],
            "until": upcoming["until"],
            "join": upcoming.get("join"),
        }
    return {
        "today": today,
        "meetings": meetings,
        "shown": list(by_id),
        "days": days,
        "banner": banner,
        "grid": {"from": 7, "to": 19, "days": grid_days, "blocks": blocks},
    }


class HubServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Client(StreamRequestHandler):
    def send(self, value: dict) -> None:
        self.wfile.write((json.dumps(value, ensure_ascii=False) + "\n").encode())
        self.wfile.flush()

    def handle(self) -> None:
        try:
            self._handle()
        except (BrokenPipeError, ConnectionResetError):
            return

    def _handle(self) -> None:
        for raw in self.rfile:
            try:
                request = json.loads(raw.decode("utf-8"))
                if request.get("token") != self.server.hub_token:
                    self.send({"error": "Invalid calendar hub token"})
                    return
                op = request.get("op")
                if op == "subscribe":
                    views = set(request.get("views", []))
                    if "meetings" in views:
                        self.send({"view": "meetings", "value": self.server.calendar.model()})
                    while True:
                        time.sleep(60)
                        if "meetings" in views:
                            self.send({"view": "meetings", "value": self.server.calendar.model()})
                elif op == "view" and request.get("name") == "meetings":
                    self.send({"value": self.server.calendar.model()})
                elif op == "act" and request.get("app") == "meetings":
                    self.send({"note": "Calendar is read-only in this first version", "pending": {}, "refreshing": {}})
                else:
                    self.send({"error": f"Unsupported calendar hub operation: {op}"})
            except (BrokenPipeError, ConnectionResetError):
                return
            except CalendarError as exc:
                self.send({"error": str(exc)})
            except Exception as exc:  # Keep the local hub alive for the next request.
                self.send({"error": f"Calendar hub error: {exc}"})


def write_hub_info(server: HubServer, token: str) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    save_json(HUB_INFO, {"port": server.server_address[1], "token": token})


def run_server() -> None:
    token = secrets.token_urlsafe(32)
    server = HubServer(("127.0.0.1", 0), Client)
    server.hub_token = token
    server.calendar = GoogleCalendar()
    write_hub_info(server, token)
    print(f"Calendar hub listening on 127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        HUB_INFO.unlink(missing_ok=True)


def main() -> int:
    command = sys.argv[1:] or ["hub", "start"]
    if command[:2] == ["hub", "start"]:
        run_server()
        return 0
    if command[:1] == ["auth"]:
        GoogleCalendar().access_token()
        print("Google Calendar authorization complete.")
        return 0
    print("Usage: calendar-cockpit.cmd hub start | auth", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
