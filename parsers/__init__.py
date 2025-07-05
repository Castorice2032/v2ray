
# لایه مرکزی برای پارس کردن لینک‌ها
from .ss import parse_ss
from .vmess import parse_vmess
from .vless import parse_vless
from .trojan import parse_trojan
from .hysteria import parse_hysteria

from .hysteria2 import parse_hysteria2
from .tuic import parse_tuic


PARSER_MAP = {
    "ss": parse_ss,
    "vmess": parse_vmess,
    "vless": parse_vless,
    "trojan": parse_trojan,
    "hysteria": parse_hysteria,
    "hysteria2": parse_hysteria2,
    "tuic": parse_tuic,
}

def parse_link(link):
    """
    نوع پروتکل را از ابتدای لینک تشخیص داده و به پارسر مناسب ارجاع می‌دهد.
    خروجی: dict استاندارد یا None
    """
    link = link.strip()
    for proto, parser in PARSER_MAP.items():
        if link.lower().startswith(proto+"://"):
            return parser(link)
    return None
