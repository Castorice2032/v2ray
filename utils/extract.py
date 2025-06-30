import os
import json
import base64
import re
import yaml
import requests
from collections import defaultdict
from pathlib import Path
from datetime import datetime

"""
Extract proxy links recursively and generate per‑protocol text files + JSON report.
- Proxy text files stay in data/input (same behaviour).
- Report is written to data/logs/report.json and includes a header with timestamp,
  total links and per‑protocol counts.
"""

# ─── مسیرها ───
BASE_DIR   = Path(__file__).resolve().parent
INPUT_DIR  = (BASE_DIR / "../data/input").resolve()
LOG_DIR    = (BASE_DIR / "../data/logs").resolve()
INPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

TYPE_JSON  = INPUT_DIR / "urls_type.json"   # ورودی
OUTPUT_DIR = INPUT_DIR                      # txt ها همان‌جا می‌مانند
REPORT_JSON = LOG_DIR / "report.json"      # گزارش نهایی

# ─── پروتکل‌ها ───
PATTERNS = {
    "ss":       re.compile(r"^ss://.+",       re.MULTILINE),
    "vmess":    re.compile(r"^vmess://.+",    re.MULTILINE),
    "vless":    re.compile(r"^vless://.+",    re.MULTILINE),
    "trojan":   re.compile(r"^trojan://.+",   re.MULTILINE),
    "hysteria": re.compile(r"^hysteria2?://.+", re.MULTILINE),
    "reality":  re.compile(r"^reality://.+",  re.MULTILINE),
}

# ─── helpers ───

def extract_links(text: str):
    links = defaultdict(list)
    for line in text.splitlines():
        line = line.strip()
        for proto, pat in PATTERNS.items():
            if pat.match(line):
                links[proto].append(line)
                break
    return links


def extract_from_clash_yaml(text: str):
    links = defaultdict(list)
    extra_urls = set()
    try:
        data = yaml.safe_load(text)
        for proxy in data.get("proxies", []):
            ptype = proxy.get("type")
            if ptype == "ss":
                userinfo = f"{proxy.get('cipher','')}:{proxy.get('password','')}"
                b64 = base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip("=")
                links["ss"].append(f"ss://{b64}@{proxy.get('server')}:{proxy.get('port')}")
            elif ptype == "vmess":
                vm_b64 = base64.urlsafe_b64encode(json.dumps(proxy).encode()).decode().rstrip("=")
                links["vmess"].append(f"vmess://{vm_b64}")
            elif ptype == "vless":
                links["vless"].append(f"vless://{proxy.get('uuid')}@{proxy.get('server')}:{proxy.get('port')}")
            elif ptype == "trojan":
                links["trojan"].append(f"trojan://{proxy.get('password')}@{proxy.get('server')}:{proxy.get('port')}")
        for prov in data.get("proxy-providers", {}).values():
            if url := prov.get("url"):
                extra_urls.add(url)
        def dig(obj):
            if isinstance(obj, dict):
                if "url" in obj: extra_urls.add(obj["url"])
                for v in obj.values(): dig(v)
            elif isinstance(obj, list):
                for itm in obj: dig(itm)
        dig(data)
    except Exception:
        pass
    return links, extra_urls


def fetch(url: str) -> str:
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

# ─── main ───

def main():
    if not TYPE_JSON.exists():
        print(f"❌ {TYPE_JSON} not found")
        return

    type_list = json.loads(TYPE_JSON.read_text(encoding="utf-8"))

    all_links      = defaultdict(list)
    report_entries = {}
    queue, seen = [], set()

    for item in type_list:
        if item.get("type") != "error":
            queue.append((item["url"], item.get("type", "unknown")))

    while queue:
        url, typ = queue.pop(0)
        if url in seen: continue
        seen.add(url)
        try:
            content = fetch(url)
            links, extra = defaultdict(list), set()
            if typ.startswith("subscription"):
                decoded = None
                try: decoded = base64.b64decode(content).decode(errors="ignore")
                except Exception: pass
                links = extract_links(decoded or content)
            elif typ == "clash_yaml":
                links, extra = extract_from_clash_yaml(content)
            else:
                links = extract_links(content)

            for proto, lst in links.items():
                all_links[proto].extend(lst)
            report_entries[url] = {
                "type": typ,
                "total": sum(len(v) for v in links.values()),
                "per_protocol": {p: len(lst) for p, lst in links.items() if lst}
            }
            for ex in extra:
                if ex not in seen:
                    qtype = "clash_yaml" if ex.endswith((".yaml", ".yml")) else "subscription_plain"
                    queue.append((ex, qtype))
        except Exception as e:
            report_entries[url] = {"type": typ, "error": str(e)}

    # ‑‑ ذخیره فایل‌های پروکسی
    for proto, lst in all_links.items():
        (OUTPUT_DIR / f"{proto}.txt").write_text("\n".join(lst), encoding="utf-8")

    # ‑‑ ساخت هدر گزارش
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_all = sum(len(v) for v in all_links.values())
    per_proto = {p: len(v) for p, v in all_links.items() if v}

    header = {
        "generated_at": timestamp,
        "total_links": total_all,
        "per_protocol_summary": per_proto
    }

    final_report = {
        **header,
        "items": report_entries
    }

    REPORT_JSON.write_text(json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Finished. Proxies saved to {OUTPUT_DIR}, report → {REPORT_JSON}")

if __name__ == "__main__":
    main()
