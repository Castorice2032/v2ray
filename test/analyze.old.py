import os
import json
import time
import socket
import re

INPUT_DIR = os.path.join(os.path.dirname(__file__), '../data/input')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/output/servers_report.json')

# Mapping of file to protocol
PROTOCOL_MAP = {
    'vmess.txt': 'vmess',
    'vless.txt': 'vless',
    'ss.txt': 'shadowsocks',
    'trojan.txt': 'trojan',
    'hysteria.txt': 'hysteria',
}

def extract_server_info(line, protocol):
    """
    Try to extract server name, address, and region from the link.
    Returns: dict with keys: name, address, region, link
    """
    # Default values
    name = None
    address = None
    region = None
    link = line.strip()
    
    # Try to extract address (host) from the link
    if protocol in ['vmess', 'vless', 'trojan', 'hysteria']:
        m = re.search(r'@([\w\.-]+)', link)
        if m:
            address = m.group(1)
    elif protocol == 'shadowsocks':
        m = re.search(r'#(.+)$', link)
        if m:
            name = m.group(1)
        m = re.search(r'@([\w\.-]+):', link)
        if m:
            address = m.group(1)
    # Try to extract name from tag or comment
    if not name:
        m = re.search(r'#(.+)$', link)
        if m:
            name = m.group(1)
    if not name:
        name = address or protocol
    # Region: try to guess from name
    if name:
        for r in ['iran', 'us', 'uk', 'germany', 'france', 'turkey', 'nl', 'ru', 'uae', 'singapore', 'japan', 'korea', 'canada']:
            if r in name.lower():
                region = r
                break
    return {
        'name': name,
        'address': address,
        'region': region,
        'link': link
    }

def ping(host, timeout=2):
    """Ping a host, return latency in ms or None if unreachable."""
    try:
        start = time.time()
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, 443))
        s.close()
        latency = int((time.time() - start) * 1000)
        return latency
    except Exception:
        return None

def analyze():
    results = []
    all_links = []
    # جمع‌آوری همه لینک‌ها و پروتکل‌ها
    for fname, protocol in PROTOCOL_MAP.items():
        fpath = os.path.join(INPUT_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                all_links.append((line, protocol))

    total = len(all_links)
    print(f"Total links detected: {total}")
    for idx, (line, protocol) in enumerate(all_links, 1):
        info = extract_server_info(line, protocol)
        if info['address']:
            latency = ping(info['address'])
        else:
            latency = None
        results.append({
            'name': info['name'],
            'protocol': protocol,
            'ping': latency,
            'region': info['region'],
            'link': info['link']
        })
        # نمایش پروگرس بار و لاگ یک خطی
        print(f"\rAnalyzing {idx}/{total} | {info['name']} | {protocol} | Ping: {latency if latency is not None else 'Timeout'}   ", end='', flush=True)
    print()  # خط جدید بعد از اتمام
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Analysis complete. Results saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    analyze()
