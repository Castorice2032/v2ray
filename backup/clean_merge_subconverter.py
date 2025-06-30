#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ادغام و پالایش سابسکریپشن‌های Clash از طریق Subconverter
Author: ChatGPT (o3)
"""

import re
import sys
import yaml
import argparse
import requests
from urllib.parse import quote_plus
from collections import defaultdict

###############################################################################
# تنظیمات کاربر
###############################################################################

URLS = [
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/gist_config/zzzZZzzZZee_clash.yaml",
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/top_size/yb_v2rayse_sub.yaml",
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/top_size/yb_v2rayse_sub1.yaml",
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/gist_config/xiaotu9639_clash.yaml",
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/github_config/Surfboardv2ray_Proxy-sorter_clash.yaml",
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/github_config/freeorgOP.yaml",
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/gist_config/CKCat_clash.yaml",
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/gist_config/ye4241_clash.yaml",
    "https://gitlab.com/wybgit/surge_conf/-/raw/main/gist_config/Cyndri_clash.yaml",
]

SUBCONVERTER_BASE = "http://127.0.0.1:25500"  # در صورت نیاز تغییر بده

# فقط cipherهای مجاز برای Shadowsocks در Clash رسمی
ALLOWED_SS_CIPHERS = {
    "aes-128-gcm",
    "aes-192-gcm",
    "aes-256-gcm",
    "chacha20-ietf-poly1305",
}

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

###############################################################################
# توابع کمکی
###############################################################################

def is_valid_uuid(value: str) -> bool:
    return bool(UUID_RE.fullmatch(value.strip()))

def is_valid_port(p) -> bool:
    try:
        n = int(p)
        return 0 < n < 65536
    except Exception:
        return False

def is_valid_proxy(item: dict) -> bool:
    """بررسی سلامت هر پروکسی پس از خروجی Subconverter"""
    if not isinstance(item, dict):
        return False

    ptype = str(item.get("type", "")).lower()

    # VMess / VLESS
    if ptype in {"vmess", "vless"}:
        ok = (
            all(item.get(k) for k in ("name", "server", "port", "uuid"))
            and is_valid_uuid(item["uuid"])
            and is_valid_port(item["port"])
        )
        # شرط Clash: برای network=h2 یا grpc باید tls روشن باشد
        net = str(item.get("network", "")).lower()
        if net in {"h2", "grpc"} and not item.get("tls", True):
            return False
        return ok

    # Trojan
    elif ptype == "trojan":
        return (
            all(item.get(k) for k in ("name", "server", "port", "password"))
            and is_valid_port(item["port"])
        )

    # Shadowsocks
    elif ptype == "ss":
        cipher = str(item.get("cipher", "")).lower()
        return (
            all(item.get(k) for k in ("name", "server", "port", "cipher", "password"))
            and is_valid_port(item["port"])
            and cipher in ALLOWED_SS_CIPHERS
        )

    # سایر انواع فعلاً پذیرفته نمی‌شوند
    return False

def fetch_from_subconverter(urls):
    """urls: list[str] → خروجی YAML (str)"""
    combined_urls = "|".join(urls)
    params = {
        "target": "clash",
        "url": combined_urls,
        "udp": "true",
        "sort": "true",
        "emoji": "true",
        "list": "false",
    }
    query = "&".join(f"{k}={quote_plus(v)}" for k, v in params.items())
    final_url = f"{SUBCONVERTER_BASE}/sub?{query}"

    print(f"[INFO] درخواست به Subconverter: {final_url}")

    r = requests.get(final_url, timeout=60)
    r.raise_for_status()
    return r.text

###############################################################################
# پردازش اصلی
###############################################################################

def main(outfile: str = "merged_clean.yaml"):
    try:
        yaml_text = fetch_from_subconverter(URLS)
    except Exception as exc:
        sys.exit(f"[ERROR] دریافت از Subconverter شکست خورد → {exc}")

    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        sys.exit(f"[ERROR] پارس YAML خروجی ناموفق → {exc}")

    proxies = data.get("proxies", []) if isinstance(data, dict) else []
    if not proxies:
        sys.exit("[ERROR] خروجی Subconverter خالی است یا فرمت نامعتبر دارد.")

    # فیلتر نهایی
    name_count = defaultdict(int)
    clean_proxies = []
    for item in proxies:
        if not is_valid_proxy(item):
            continue

        base = str(item["name"])
        name_count[base] += 1
        if name_count[base] > 1:
            item["name"] = f"{base} ({name_count[base]})"
        clean_proxies.append(item)

    if not clean_proxies:
        sys.exit("[ERROR] پس از فیلتر، پروکسی سالمی باقی نماند!")

    # جایگزینی لیست پروکسی‌ها در خروجی اصلی
    data["proxies"] = clean_proxies
    data["proxy-groups"] = [
        {
            "name": "♻️ Auto",
            "type": "url-test",
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
            "proxies": [p["name"] for p in clean_proxies],
        }
    ]
    data["rules"] = ["MATCH,♻️ Auto"]

    with open(outfile, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    print(f"✅ {outfile} نوشته شد؛ {len(clean_proxies)} نود سالم اضافه شد.")

###############################################################################
# اجرای اسکریپت
###############################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge & clean Clash subscriptions via Subconverter"
    )
    parser.add_argument(
        "-o", "--output", default="merged_clean.yaml", help="نام فایل خروجی"
    )
    parser.add_argument(
        "-s",
        "--subconverter",
        default=SUBCONVERTER_BASE,
        help="آدرس Subconverter مثل http://IP:25500",
    )
    args = parser.parse_args()

    SUBCONVERTER_BASE = args.subconverter.rstrip("/")
    main(outfile=args.output)
