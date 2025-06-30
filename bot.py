import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MESSAGE = os.getenv('TELEGRAM_MESSAGE', '🔔 Proxy servers updated. Check the latest list!')

if not TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env file")

url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
data = {
    'chat_id': CHAT_ID,
    'text': MESSAGE,
    'parse_mode': 'Markdown'
}

res = requests.post(url, data=data)
print(res.json())
