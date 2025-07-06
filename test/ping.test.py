# Test for ckecker/ping.py
import sys, os, time
from pathlib import Path

# allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ckecker.ping import ping_host, ping_hosts


def main():
    # Define a variety of 10 hosts (local, popular domains, firewalled/unreachable)
    hosts = [
        "127.0.0.1",       # local
        "chatgpt.com",     # ChatGPT service
        "google.com",      # popular site
        "cloudflare.com",  # CDN
        "amazon.com",      # e-commerce
        "facebook.com",    # social media
        "twitter.com",     # social media
        "youtube.com",     # streaming
        "192.0.2.1",       # TEST-NET-1 unreachable
        "203.0.113.5"      # TEST-NET-3 unreachable
    ]

    print("=== Testing ping_host (10 pings each, timeout=2s) ===")
    for host in hosts:
        start = time.time()
        ok = ping_host(host, count=10, timeout=2)
        latency = int((time.time() - start) * 1000)
        status = 'reachable' if ok else 'unreachable'
        print(f"{host:20} -> {status:11} ({latency}ms)")

    print("\n=== Testing ping_hosts (concurrent, 10 pings, timeout=2s) ===")
    start = time.time()
    results = ping_hosts(hosts, count=10, timeout=2, concurrency=5)
    duration = int((time.time() - start) * 1000)
    for res in results:
        status = 'reachable' if res['reachable'] else 'unreachable'
        print(f"{res['host']:20} -> {status}")
    print(f"Concurrent ping_hosts completed in {duration}ms")

if __name__ == "__main__":
    main()
