import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()



TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# همهٔ کلیدهایی که با TELEGRAM_ و …CHANNEL ختم می‌شوند را جمع می‌کنیم
channel_vars = [
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_VMESS_CHANNEL",
    "TELEGRAM_V2RAY_CHANNEL",
    "TELEGRAM_TROJAN_CHANNEL",
    "TELEGRAM_SS_CHANNEL",
    "TELEGRAM_HYSTERIA_CHANNEL",
    "TELEGRAM_CLASH_CHANNEL",
]

channels = [os.getenv(v) for v in channel_vars if os.getenv(v)]

MESSAGE = "🔔 *Test*: New proxy list is ready!"
keyboard = {
    "inline_keyboard": [
        [
            {"text": "دانلود Vmess", "url": "https://example.com/vmess.txt"},
            {"text": "دانلود SS",    "url": "https://example.com/ss.txt"}
        ],
        [
            {"text": "گزارش کامل",   "url": "https://example.com/report.json"}
        ]
    ]
}
payload_template = {
    "text": MESSAGE,
    "parse_mode": "Markdown",
    "disable_web_page_preview": True,
    "reply_markup": keyboard
}

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

for chat_id in channels:
    payload = {**payload_template, "chat_id": chat_id}
    r = requests.post(url, json=payload, timeout=15)
    print(chat_id, r.json())
