import os
import json
import base64
import re
import yaml
import requests
from collections import defaultdict

TYPE_JSON = os.path.join(os.path.dirname(__file__), '../sources/type.json')
PROXY_DIR = os.path.dirname(__file__)

# پروتکل‌های پشتیبانی‌شده
PROTOCOLS = ["ss", "vmess", "vless", "trojan", "hysteria", "reality"]
PATTERNS = {
    "ss": re.compile(r"^ss://.+", re.MULTILINE),
    "vmess": re.compile(r"^vmess://.+", re.MULTILINE),
    "vless": re.compile(r"^vless://.+", re.MULTILINE),
    "trojan": re.compile(r"^trojan://.+", re.MULTILINE),
    "hysteria": re.compile(r"^hysteria2?://.+", re.MULTILINE),
    "reality": re.compile(r"^reality://.+", re.MULTILINE),
}

def extract_links(text):
    """استخراج لینک‌های پروکسی از متن ساده"""
    links = defaultdict(list)
    for line in text.splitlines():
        line = line.strip()
        for proto, pat in PATTERNS.items():
            if pat.match(line):
                links[proto].append(line)
                break
    return links

def extract_from_clash_yaml(text):
    """استخراج لینک از فایل yaml (کلش)"""
    links = defaultdict(list)
    extra_urls = set()
    try:
        data = yaml.safe_load(text)
        proxies = data.get('proxies', [])
        for proxy in proxies:
            if proxy.get('type') == 'ss':
                userinfo = f"{proxy.get('cipher','')}:{proxy.get('password','')}"
                userinfo_b64 = base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip('=')
                link = f"ss://{userinfo_b64}@{proxy.get('server','')}:{proxy.get('port','')}"
                links['ss'].append(link)
            elif proxy.get('type') == 'vmess':
                vmess_json = json.dumps(proxy, ensure_ascii=False)
                vmess_b64 = base64.urlsafe_b64encode(vmess_json.encode()).decode().rstrip('=')
                link = f"vmess://{vmess_b64}"
                links['vmess'].append(link)
            elif proxy.get('type') == 'vless':
                user = proxy.get('uuid','')
                link = f"vless://{user}@{proxy.get('server','')}:{proxy.get('port','')}"
                links['vless'].append(link)
            elif proxy.get('type') == 'trojan':
                link = f"trojan://{proxy.get('password','')}@{proxy.get('server','')}:{proxy.get('port','')}"
                links['trojan'].append(link)
        # استخراج subscription و proxy-providers
        providers = data.get('proxy-providers', {})
        for prov in providers.values():
            url = prov.get('url')
            if url:
                extra_urls.add(url)
        # استخراج url از سایر بخش‌ها (subscriptionها)
        for k, v in data.items():
            if isinstance(v, dict) and 'url' in v:
                extra_urls.add(v['url'])
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and 'url' in item:
                        extra_urls.add(item['url'])
    except Exception as e:
        pass
    return links, extra_urls

def fetch_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text

def main():
    with open(TYPE_JSON, encoding="utf-8") as f:
        type_list = json.load(f)
    all_links = defaultdict(list)
    report = []
    seen_urls = set()
    queue = []
    url_to_report = {}
    url_to_children = defaultdict(list)
    url_to_child_stats = defaultdict(lambda: defaultdict(int))
    for item in type_list:
        url = item.get('url')
        typ = item.get('type')
        protocols = item.get('protocols', [])
        if not url or typ == 'error':
            continue
        queue.append((url, typ, protocols, None))  # None = no parent
    while queue:
        url, typ, protocols, parent_url = queue.pop(0)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            content = fetch_content(url)
            links = defaultdict(list)
            extra_urls = set()
            if typ == 'subscription_base64':
                decoded = base64.b64decode(content.strip()).decode(errors="ignore")
                links = extract_links(decoded)
            elif typ == 'subscription_plain':
                links = extract_links(content)
            elif typ == 'clash_yaml':
                links, extra_urls = extract_from_clash_yaml(content)
            else:
                links = extract_links(content)
            link_count = 0
            proto_count = {}
            for proto, lst in links.items():
                all_links[proto].extend(lst)
                proto_count[proto] = len(lst)
                link_count += len(lst)
            url_to_report[url] = {
                "url": url,
                "type": typ,
                "protocols": protocols,
                "total_links": link_count,
                "per_protocol": proto_count,
                "child_extracted": 0,
                "child_per_protocol": {},
                "child_urls": []
            }
            if parent_url:
                url_to_children[parent_url].append(url)
            for extra_url in extra_urls:
                if extra_url not in seen_urls:
                    if extra_url.endswith('.yaml') or extra_url.endswith('.yml'):
                        queue.append((extra_url, 'clash_yaml', [], url))
                    elif extra_url.endswith('.txt') or extra_url.endswith('.list') or extra_url.endswith('.sub'):
                        queue.append((extra_url, 'subscription_plain', [], url))
                    else:
                        queue.append((extra_url, 'subscription_plain', [], url))
        except Exception as e:
            url_to_report[url] = {
                "url": url,
                "type": typ,
                "error": str(e),
                "child_extracted": 0,
                "child_per_protocol": {},
                "child_urls": []
            }
            if parent_url:
                url_to_children[parent_url].append(url)
    # جمع‌آوری آمار فرزندها برای هر مادر
    for url, report_item in url_to_report.items():
        children = url_to_children.get(url, [])
        child_total = 0
        child_proto = defaultdict(int)
        for child_url in children:
            child = url_to_report.get(child_url, {})
            child_total += child.get('total_links', 0)
            for proto, count in child.get('per_protocol', {}).items():
                child_proto[proto] += count
        report_item['child_extracted'] = child_total
        report_item['child_per_protocol'] = dict(child_proto)
        report_item['child_urls'] = children
    # ساخت گزارش نهایی
    report = list(url_to_report.values())
    for proto, lst in all_links.items():
        with open(os.path.join(PROXY_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            for l in lst:
                f.write(l + "\n")
    with open(os.path.join(PROXY_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("Done. All proxies extracted and report generated (recursive mode, with parent-child stats).")

if __name__ == "__main__":
    main()
