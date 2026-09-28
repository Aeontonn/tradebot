"""Telegram-notiser. Gör inget om token saknas, så boten fungerar utan Telegram."""
import json
import urllib.parse
import urllib.request

import config


def send(text):
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        print(f"[notis] {text}")
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": config.TELEGRAM_CHAT_ID, "text": text}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15) as resp:
            return json.load(resp).get("ok", False)
    except Exception as exc:  # nätverksfel ska aldrig stoppa boten
        print(f"[telegram-fel] {exc}")
        return False
