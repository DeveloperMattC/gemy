#!/usr/bin/env python3
"""Gemy Control Center for macOS — monitor & control without overwriting board code.

Default policy: never adb push. The board may run a newer Gemy than this repo.
Opt in only with --allow-push (or env GEMY_ALLOW_PUSH=1).

  ./mac/start-hub.sh
  python3 mac/hub/hub_server.py --port 8765
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
MAC_ROOT = Path(__file__).resolve().parents[1]
MAC_WWW = Path(__file__).resolve().parent / "www"
WIN_WWW = REPO_ROOT / "windows" / "hub" / "www"
START_GEMY = MAC_ROOT / "start-gemy.sh"
CLEANUP = MAC_ROOT / "cleanup-board.sh"

ACTIVITY: list[dict[str, str]] = []
ACTIVITY_MAX = 200
ALLOW_PUSH = False
LAST_HEALTH: dict[str, Any] | None = None


def add_activity(message: str, level: str = "info") -> dict[str, str]:
    entry = {
        "time": time.strftime("%H:%M:%S"),
        "level": level,
        "message": message,
    }
    ACTIVITY.append(entry)
    while len(ACTIVITY) > ACTIVITY_MAX:
        ACTIVITY.pop(0)
    return entry


def run_cmd(args: list[str], timeout: float = 45) -> tuple[int, str]:
    try:
        p = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except FileNotFoundError:
        return 127, f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "timed out"


def adb(*args: str, timeout: float = 45) -> tuple[int, str]:
    return run_cmd(["adb", *args], timeout=timeout)


def adb_shell(cmd: str, timeout: float = 45) -> tuple[int, str]:
    return adb("shell", cmd, timeout=timeout)


def adb_on_path() -> bool:
    return shutil.which("adb") is not None


def board_connected() -> bool:
    code, out = adb("devices", timeout=15)
    if code != 0:
        return False
    for line in out.splitlines():
        if "\tdevice" in line:
            return True
    return False


def board_has_greeter() -> bool:
    code, out = adb_shell("test -f /home/root/greeter.py && echo yes || echo no", timeout=20)
    return code == 0 and "yes" in out


def board_has_venv() -> bool:
    code, out = adb_shell(
        "test -x /home/root/sl2610-examples/.venv/bin/python3 && echo yes || echo no",
        timeout=20,
    )
    return code == 0 and "yes" in out


def board_usb0_ip() -> str | None:
    code, out = adb_shell(
        "ip -4 addr show usb0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -1",
        timeout=20,
    )
    if code != 0:
        return None
    ip = out.strip().splitlines()[0].strip() if out.strip() else ""
    return ip or None


def get_health() -> dict[str, Any]:
    adb_ok = adb_on_path()
    connected = board_connected() if adb_ok else False
    scripts = board_has_greeter() if connected else False
    venv = board_has_venv() if connected else False
    usb0 = board_usb0_ip() if connected else None

    checks = [
        {
            "id": "adb",
            "label": "ADB tools",
            "ok": adb_ok,
            "detail": "adb on PATH" if adb_ok else "brew install android-platform-tools",
        },
        {
            "id": "host",
            "label": "Host mode",
            "ok": True,
            "detail": "Monitor only — will not push to board"
            if not ALLOW_PUSH
            else "Push allowed (--allow-push)",
        },
        {
            "id": "board",
            "label": "Board on ADB",
            "ok": connected,
            "detail": (
                f"Connected — usb0 {usb0}" if usb0 else "Connected"
            )
            if connected
            else "Plug USB-C data cable, wait ~20s for boot",
        },
    ]
    if connected:
        checks += [
            {
                "id": "scripts",
                "label": "Gemy on board",
                "ok": scripts,
                "detail": (
                    "greeter.py present (board copy left alone)"
                    if scripts
                    else "No greeter.py on board"
                ),
            },
            {
                "id": "venv",
                "label": "Speech stack",
                "ok": venv,
                "detail": "sl2610-examples venv ready" if venv else "Need sl2610-examples on board",
            },
            {
                "id": "log",
                "label": "Board log",
                "ok": True,
                "detail": "Readable via /home/root/gemy.log",
            },
        ]
    else:
        checks += [
            {"id": "scripts", "label": "Gemy on board", "ok": False, "detail": "Connect board"},
            {"id": "venv", "label": "Speech stack", "ok": False, "detail": "Connect board"},
            {"id": "log", "label": "Board log", "ok": False, "detail": "Connect board"},
        ]

    if connected:
        status, status_text = "ready", (
            f"Connected — {usb0}" if usb0 else "Connected — ready (no push)"
        )
    elif not adb_ok:
        status, status_text = "setup", "Install ADB (android-platform-tools)"
    else:
        status, status_text = "offline", "Board not on ADB"

    return {
        "status": status,
        "statusText": status_text,
        "adbOnPath": adb_ok,
        "ncmDriver": True,
        "boardConnected": connected,
        "gemyScripts": scripts,
        "speechVenv": venv,
        "bootAutostart": False,
        "bootAutostartWant": False,
        "usb0Ip": usb0,
        "checks": checks,
        "pushAllowed": ALLOW_PUSH,
        "host": "mac",
    }


def open_in_terminal(script: Path, extra_args: list[str] | None = None) -> None:
    extra = " ".join(extra_args or [])
    cmd = f'cd {REPO_ROOT.as_posix()!r} && {script.as_posix()!r} {extra}'.rstrip()
    # Open a new Terminal window so logs stream like Windows PowerShell.
    osa = f'tell application "Terminal" to do script {cmd!r}'
    subprocess.Popen(["osascript", "-e", osa], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sync_board_if_allowed() -> dict[str, Any]:
    if not ALLOW_PUSH:
        return {
            "ok": True,
            "message": "Skipped push — Mac hub never overwrites board code by default.",
            "skipped": True,
        }
    if not board_connected():
        return {"ok": False, "message": "Board not connected on ADB.", "skipped": False}

    push_list = [
        "greeter.py",
        "hat.py",
        "gemma_mood.py",
        "gemma_mood_worker.py",
        "gemy_diag.py",
        "gemy_trace.py",
        "gemy_stability.py",
        "gemy_empathy.py",
        "gemy_fallback.py",
        "gemy_classify.py",
        "gemy_math.py",
        "gemy_qa.py",
        "gemy_phrase_buffer.py",
        "gemy_heartbeat_smoke.py",
        "gemy_reactions.py",
    ]
    for name in push_list:
        local = REPO_ROOT / "board" / "python" / name
        if not local.is_file():
            continue
        code, out = adb("push", str(local), f"/home/root/{name}", timeout=60)
        if code != 0:
            return {"ok": False, "message": f"adb push failed: {name} ({out.strip()})", "skipped": False}
    return {"ok": True, "message": "Board scripts synced from this repo.", "skipped": False}


def resolve_static(rel: str) -> Path | None:
    safe = rel.lstrip("/").replace("..", "")
    if not safe:
        safe = "index.html"
    for root in (MAC_WWW, WIN_WWW):
        full = root / safe
        if full.is_file():
            return full
    return None


MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class HubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/health":
            global LAST_HEALTH
            LAST_HEALTH = get_health()
            self._json({"ok": True, "health": LAST_HEALTH, "activity": list(ACTIVITY)})
            return
        if path == "/api/activity":
            self._json({"ok": True, "activity": list(ACTIVITY)})
            return
        if path == "/api/board-log":
            if not board_connected():
                self._json({"ok": False, "lines": [], "message": "Board not connected"})
                return
            n = 80
            try:
                n = max(10, min(500, int((qs.get("lines") or ["80"])[0])))
            except ValueError:
                pass
            _, out = adb_shell(
                f"tail -n {n} /home/root/gemy.log 2>/dev/null || echo '(no gemy.log yet)'",
                timeout=30,
            )
            lines = out.splitlines()
            self._json({"ok": True, "lines": lines, "message": None})
            return
        if path == "/api/board-processes":
            if not board_connected():
                self._json({"ok": False, "processes": [], "message": "Board not connected"})
                return
            _, out = adb_shell(
                "ps aux 2>/dev/null | grep -E 'greeter|gemy-boot|gemy-watcher|moonshine' | grep -v grep || true",
                timeout=30,
            )
            procs = [ln for ln in out.splitlines() if ln.strip()]
            self._json({"ok": True, "processes": procs})
            return

        if path.startswith("/api/"):
            self._json({"ok": False, "message": "Not found"}, 404)
            return

        rel = "index.html" if path in ("/", "") else path
        file_path = resolve_static(rel)
        if not file_path:
            self._bytes(b"Not found", "text/plain", 404)
            return
        data = file_path.read_bytes()
        ctype = MIME.get(file_path.suffix.lower(), "application/octet-stream")
        self._bytes(data, ctype)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        if path == "/api/refresh":
            add_activity("Checking connection (no board push)…")
            health = get_health()
            global LAST_HEALTH
            LAST_HEALTH = health
            sync = sync_board_if_allowed()
            add_activity(sync["message"], "ok" if sync["ok"] else "error")
            add_activity(
                f"Status: {health['statusText']}",
                "ok" if health["status"] == "ready" else "info",
            )
            self._json(
                {
                    "ok": True,
                    "health": health,
                    "message": sync["message"],
                    "activity": list(ACTIVITY),
                }
            )
            return

        if path == "/api/install-driver":
            msg = "USB NCM driver install is Windows-only. On Mac, ADB over USB is enough."
            add_activity(msg, "info")
            self._json(
                {
                    "ok": True,
                    "skipped": True,
                    "message": msg,
                    "health": get_health(),
                    "activity": list(ACTIVITY),
                }
            )
            return

        if path == "/api/start-gemy":
            if not board_connected():
                add_activity("Cannot start — board not on ADB.", "error")
                self._json(
                    {
                        "ok": False,
                        "message": "Board not on ADB. Plug USB-C and refresh.",
                        "activity": list(ACTIVITY),
                    }
                )
                return
            if not board_has_greeter():
                add_activity("No greeter.py on board — not pushing from Mac hub.", "error")
                self._json(
                    {
                        "ok": False,
                        "message": "Board has no greeter.py. This hub will not push repo code.",
                        "activity": list(ACTIVITY),
                    }
                )
                return

            no_vision = bool(body.get("noVision", True))
            no_gemma = bool(body.get("noGemmaMood", False))
            args: list[str] = ["--no-push"]
            if no_vision:
                args.append("--no-vision")
            if no_gemma:
                args.append("--no-gemma-mood")
            if not START_GEMY.is_file():
                self._json({"ok": False, "message": f"Missing {START_GEMY}", "activity": list(ACTIVITY)})
                return
            open_in_terminal(START_GEMY, args)
            mode = "keywords only, no Gemma" if no_gemma else "board default moods"
            label = f"Gemy voice ({mode})" if no_vision else f"Gemy camera+voice ({mode})"
            add_activity(f"Launched {label} — see Terminal for [ears] listening.", "ok")
            self._json(
                {
                    "ok": True,
                    "message": f"Launched {label}. Wait for [ears] listening, then speak.",
                    "activity": list(ACTIVITY),
                }
            )
            return

        if path == "/api/hat-panel":
            if not board_connected():
                self._json({"ok": False, "message": "Board not on ADB", "activity": list(ACTIVITY)})
                return
            # Quick HAT smoke via adb (Windows has a WinForms panel).
            add_activity("Running hat.py beep (board-resident)…")
            code, out = adb_shell("python3 /home/root/hat.py beep 2>&1 | tail -5", timeout=30)
            msg = out.strip() or ("beep ok" if code == 0 else "hat.py failed")
            add_activity(msg, "ok" if code == 0 else "error")
            self._json({"ok": code == 0, "message": msg, "activity": list(ACTIVITY)})
            return

        if path == "/api/cleanup":
            if not CLEANUP.is_file():
                self._json({"ok": False, "message": f"Missing {CLEANUP}", "activity": list(ACTIVITY)})
                return
            add_activity("Stopping demos and turning buzzer off…")
            code, out = run_cmd(["bash", str(CLEANUP)], timeout=90)
            for line in out.splitlines():
                if line.strip():
                    add_activity(line.strip())
            add_activity("Board cleanup finished.", "ok" if code == 0 else "warn")
            health = get_health()
            self._json(
                {
                    "ok": True,
                    "message": "Cleanup done",
                    "health": health,
                    "activity": list(ACTIVITY),
                }
            )
            return

        self._json({"ok": False, "message": "Not found"}, 404)


def find_port(preferred: int) -> int:
    import socket

    for port in [preferred] + list(range(8766, 8776)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found for Control Center (8765-8775).")


def main() -> int:
    global ALLOW_PUSH
    parser = argparse.ArgumentParser(description="Gemy Control Center (macOS)")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--allow-push",
        action="store_true",
        help="Allow adb push of repo board/python onto the Coralboard (off by default)",
    )
    args = parser.parse_args()
    ALLOW_PUSH = bool(args.allow_push or os.environ.get("GEMY_ALLOW_PUSH") == "1")

    if sys.platform != "darwin":
        print("Note: this hub is intended for macOS; continuing anyway.", file=sys.stderr)

    port = args.port if args.port > 0 else find_port(8765)
    server = ThreadingHTTPServer(("127.0.0.1", port), HubHandler)
    url = f"http://127.0.0.1:{port}/"
    mode = "PUSH ALLOWED" if ALLOW_PUSH else "no push (board code protected)"
    print("")
    print(f"  Gemy Control Center (Mac) — {mode}")
    print(f"  {url}")
    print("  Keep this terminal open while using the UI.")
    print("")
    add_activity(f"Hub started ({mode})")

    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
