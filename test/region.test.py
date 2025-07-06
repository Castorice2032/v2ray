# Test for ckecker/region.py
import sys, os
from pathlib import Path

# allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ckecker.region import ensure_geolite_db, get_country

# List of 10 diverse IP addresses for testing region lookup
test_ips = [
    "8.8.8.8",        # USA (Google DNS)
    "1.1.1.1",        # USA (Cloudflare DNS)
    "91.198.174.192", # NL (Wikipedia)
    "210.140.131.1",  # JP (Yahoo Japan)
    "149.28.148.230", # US (DigitalOcean)
    "51.158.68.68",   # FR (OVH)
    "2001:4860:4860::8888", # IPv6 Google DNS (US)
    "140.82.113.3",   # US (GitHub)
    "13.35.16.82",    # IE (Amazon)
    "185.60.216.35"   # IE (Facebook)
]

if __name__ == "__main__":
    print("=== Region Lookup Test (MaxMind DB) ===")
    # Ensure local GeoLite2 database is downloaded
    try:
        ensure_geolite_db()
        print("GeoLite2 database ready.")
    except Exception as e:
        print(f"Failed to prepare GeoLite2 DB: {e}")
    for ip in test_ips:
        try:
            country = get_country(ip)
        except Exception as e:
            country = f"ERROR: {e}"
        print(f"{ip:39} -> {country}")
