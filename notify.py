"""Telegram notifications. Does nothing if the token is missing, so the bot works without Telegram."""
import json
import urllib.parse
import urllib.request

import config


def send(text):
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        print(f"[notify] {text}")
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": config.TELEGRAM_CHAT_ID, "text": text}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15) as resp:
            return json.load(resp).get("ok", False)
    except Exception as exc:  # network errors must never stop the bot
        print(f"[telegram-error] {exc}")
        return False
