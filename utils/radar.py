"""
radar.py - Proxy Subscription Type Detector

This script reads a list of URLs (proxy subscription links) from a file, fetches their content, and detects the type and protocol(s) of each subscription or configuration. It supports various proxy formats such as vmess, vless, trojan, ss, reality, hysteria, Clash YAML, and Singbox JSON. The results are saved as a JSON summary for further processing or analysis.

Responsibilities:
- Fetches URLs concurrently.
- Detects proxy type and protocol(s) using regex and content analysis.
- Handles base64-encoded and plain text subscriptions.
- Outputs a structured JSON report.

"""

import requests
import json
import re
import base64
from concurrent.futures import ThreadPoolExecutor

URLS_FILE = "../urls.txt"
OUTPUT_FILE = "../data/json/urls_type.json"

# Regex patterns for proxy types
PATTERNS = {
    "vmess": re.compile(r"^vmess://", re.MULTILINE),
    "vless": re.compile(r"^vless://", re.MULTILINE),
    "trojan": re.compile(r"^trojan://", re.MULTILINE),
    "ss": re.compile(r"^ss://", re.MULTILINE),
    "reality": re.compile(r"^reality://", re.MULTILINE),
    "hysteria": re.compile(r"^hysteria2?://", re.MULTILINE),
    "clash_yaml": re.compile(r"(?i)(proxies:|proxy-groups:|^#yaml|\.ya?ml$)", re.MULTILINE),
    "json": re.compile(r"^\s*\{.*\}\s*$", re.DOTALL),
    "singbox_json": re.compile(r'"outbounds"\s*:\s*\[', re.MULTILINE),  # Detect Singbox structure
}


def is_base64(s):
    s = s.strip()
    if len(s) < 16:
        return False
    if not re.fullmatch(r'[A-Za-z0-9+/=\n\r]+', s):
        return False
    try:
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False


def detect_subscription_type(decoded):
    lines = [l.strip() for l in decoded.splitlines() if l.strip()]
    protocols = set()
    for l in lines:
        for t, pat in PATTERNS.items():
            if t not in ("clash_yaml", "json") and pat.match(l):
                protocols.add(t)
    return {
        "category": "subscription",
        "protocols": sorted(protocols),
        "valid": bool(protocols),
        "raw_lines": len(lines)
    }


def detect_type(text, url=None):
    # 1. Singbox JSON (special structure)
    if PATTERNS["singbox_json"].search(text):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "outbounds" in data:
                outbounds = data["outbounds"]
                protocols = set()
                for node in outbounds:
                    proto = node.get("type")
                    if proto:
                        protocols.add(proto)
                return {
                    "category": "json",
                    "type": "singbox_json",
                    "format": "object",
                    "encoding": "plain",
                    "protocols": sorted(protocols),
                    "description": f"Singbox JSON config with {len(outbounds)} outbounds ({', '.join(sorted(protocols))})"
                }
        except Exception:
            pass
    # 2. Clash YAML
    if PATTERNS["clash_yaml"].search(text):
        return {
            "category": "yaml",
            "type": "clash_yaml",
            "format": "object",
            "encoding": "plain",
            "description": "Clash YAML object (proxy list or config)"
        }
    # 3. JSON object
    if PATTERNS["json"].match(text):
        return {
            "category": "json",
            "type": "proxy_object_json",
            "format": "object",
            "encoding": "plain",
            "description": "Proxy object in JSON format"
        }
    # 4. Base64 subscription
    if is_base64(text):
        try:
            decoded = base64.b64decode(text.strip()).decode(errors="ignore")
            sub_type = detect_subscription_type(decoded)
            sub_type.update({
                "type": "subscription_base64" if sub_type["valid"] else "subscription_base64_invalid",
                "encoding": "base64",
                "format": "subscription_list",
                "description": "Base64-encoded subscription list (each line is a proxy link, protocols detected)"
            })
            return sub_type
        except Exception:
            return {
                "category": "subscription",
                "type": "subscription_base64_invalid",
                "encoding": "base64",
                "format": "subscription_list",
                "valid": False,
                "protocols": [],
                "description": "Invalid base64-encoded subscription list"
            }
    # 5. Plain text subscription (multi-line)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines:
        valid_lines = []
        invalid_lines = []
        for l in lines:
            if any(PATTERNS[t].match(l) for t in PATTERNS if t not in ("clash_yaml", "json", "singbox_json")):
                valid_lines.append(l)
            else:
                invalid_lines.append(l)
        if len(valid_lines) >= 2:  # At least two valid links to detect subscription
            sub_type = detect_subscription_type("\n".join(valid_lines))
            sub_type.update({
                "type": "subscription_plain" if sub_type["valid"] else "subscription_plain_invalid",
                "encoding": "plain",
                "format": "subscription_list",
                "description": f"Plain text subscription list (valid proxy links: {len(valid_lines)}, ignored lines: {len(invalid_lines)})"
            })
            return sub_type
    # 6. Single proxy link
    for t, pat in PATTERNS.items():
        if t not in ("clash_yaml", "json", "singbox_json") and pat.match(text.strip()):
            return {
                "category": "single_proxy",
                "type": t,
                "format": "single_proxy_link",
                "encoding": "plain",
                "protocols": [t],
                "description": f"Single {t} proxy link"
            }
    # 7. Unknown
    return {
        "category": "unknown",
        "type": "unknown",
        "format": "unknown",
        "encoding": "plain",
        "protocols": [],
        "description": "Unknown or unsupported format"
    }


def fetch_and_detect(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
        content = resp.text
        ftype = detect_type(content, url)
        result = {"url": url}
        result.update(ftype)
        return result
    except Exception as e:
        return {"url": url, "type": "error", "error": str(e)}

from datetime import datetime
def main():
    with open(URLS_FILE, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for result in executor.map(fetch_and_detect, urls):
            results.append(result)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary = {
        "updated_at": now,
        "total_urls": len(urls),
        "total_processed": len(results)
    }
    output = {
        "summary": summary,
        "items": results
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Done. Results written to {OUTPUT_FILE}")
    print(f"Updated at: {now} | Total URLs: {len(urls)} | Processed: {len(results)}")

if __name__ == "__main__":
    main()
