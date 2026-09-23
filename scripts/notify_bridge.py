#!/usr/bin/env python3
"""Text Misty the booking alerts queued in Supabase, using this Mac's Messages app.

Runs every minute from launchd (see install-notify-bridge.sh). The secret token
lives in ~/Library/Application Support/BrassyMonkeyNotify/config.env, never in git.
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime

SB_URL = "https://kaopminkiwnjtednhmxq.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imthb3BtaW5raXduanRlZG5obXhxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcxODYzNTgsImV4cCI6MjEwMjc2MjM1OH0.mIjPx1nIxVmbxKj6YX7_7rLNLJkzRWvdY6JKg8OiD-U"
CONFIG = os.path.expanduser("~/Library/Application Support/BrassyMonkeyNotify/config.env")

SEND_SCRIPT = """
on run argv
  set theNumber to item 1 of argv
  set theText to item 2 of argv
  tell application "Messages"
    set smsService to first account whose service type is SMS
    send theText to buddy theNumber of smsService
  end tell
end run
"""


def log(msg):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def load_config():
    conf = {}
    if os.path.exists(CONFIG):
        with open(CONFIG) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    conf[k.strip()] = v.strip().strip('"')
    return conf


def rpc(name, payload):
    req = urllib.request.Request(
        f"{SB_URL}/rest/v1/rpc/{name}",
        data=json.dumps(payload).encode(),
        headers={
            "apikey": SB_KEY,
            "Authorization": f"Bearer {SB_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read()
        return json.loads(body) if body else None


def send_text(number, text):
    res = subprocess.run(
        ["/usr/bin/osascript", "-e", SEND_SCRIPT, number, text],
        capture_output=True, text=True, timeout=60,
    )
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout).strip() or f"osascript exit {res.returncode}")


def main():
    conf = load_config()
    token = conf.get("NOTIFY_TOKEN")
    if not token:
        log("missing NOTIFY_TOKEN in config.env")
        return 1
    dry_run = conf.get("DRY_RUN") == "1"
    to_override = conf.get("TO_OVERRIDE") or None

    try:
        items = rpc("notify_pull", {"p_token": token}) or []
    except Exception as e:
        log(f"pull failed: {e}")
        return 1

    for item in items:
        number = to_override or item["phone"]
        if dry_run:
            log(f"DRY RUN #{item['id']} -> {number}: {item['body']}")
            continue
        try:
            send_text(number, item["body"])
            rpc("notify_mark", {"p_token": token, "p_id": item["id"], "p_ok": True})
            log(f"sent #{item['id']} -> {number}")
        except Exception as e:
            rpc("notify_mark", {"p_token": token, "p_id": item["id"], "p_ok": False, "p_error": str(e)})
            log(f"send failed #{item['id']}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
