import os
import requests
from dotenv import load_dotenv
load_dotenv()

TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MESSAGE = "🔔 لیست جدید پروکسی‌ها آماده شد!"

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

payload = {
    "chat_id": CHAT_ID,
    "text": MESSAGE,
    "parse_mode": "Markdown",
    "disable_web_page_preview": True,
    "reply_markup": keyboard
}

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
res = requests.post(url, json=payload)
print(res.json())
