import requests

TOKEN = '7787890538:AAHFg5Lpgz7byfR461jyoPY7W6P9bYmnMNU'
CHAT_ID = '@netnestvpn' 
MESSAGE = '🔔 Proxy servers updated. Check the latest list!'

url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
data = {
    'chat_id': CHAT_ID,
    'text': MESSAGE,
    'parse_mode': 'Markdown'
}

res = requests.post(url, data=data)
print(res.json())
