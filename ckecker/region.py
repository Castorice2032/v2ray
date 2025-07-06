"""
Module for determining server region (country) based on IP using MaxMind GeoLite2 database.
"""
import ipaddress
from pathlib import Path
from typing import Optional
import socket
try:
    from geoip2.database import Reader
except ImportError:
    Reader = None  # Will raise if not installed
import requests
import gzip
import shutil
import os

# Default path to the GeoLite2-Country.mmdb file
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "GeoLite2-Country.mmdb"

def ensure_geolite_db(db_path: Path = DEFAULT_DB_PATH, url: Optional[str] = None):
    """
    Ensure the GeoLite2 country DB exists locally, download and extract if missing.
    Silently skip on any error and rely on fallback API.
    """
    if db_path.exists():
        return
    try:
        # Create directory
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Default download URL for GeoLite2-Country
        dl_url = url or "https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz"
        gz_path = db_path.with_suffix(db_path.suffix + ".gz")
        # Download
        resp = requests.get(dl_url, stream=True, timeout=30)
        if resp.status_code != 200:
            return
        with open(gz_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        # Extract gzip
        with gzip.open(gz_path, 'rb') as f_in:
            with open(db_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(gz_path)
    except Exception:
        # skip failures, fallback to API
        return

def get_country(ip: str, db_path: Optional[str] = None) -> Optional[str]:
    """
    Return the ISO country code for the given IP using the MaxMind database.
    Returns None if lookup fails or IP is invalid.
    """
    # Resolve domain names to IP
    try:
        # If valid IP literal, keep
        ip_obj = ipaddress.ip_address(ip)
        ip_str = ip
    except ValueError:
        try:
            ip_str = socket.gethostbyname(ip)
        except Exception:
            return None

    # Determine database path
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    # Ensure local DB
    if Reader:
        ensure_geolite_db(Path(path))
    # Try MaxMind DB lookup
    if Reader and path.exists():
        try:
            with Reader(str(path)) as reader:
                response = reader.country(ip)
                return response.country.iso_code
        except Exception:
            pass
    # Fallback to external IP geolocation API
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,countryCode"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data.get("status") == "success":
            return data.get("countryCode")
    except Exception:
        pass
    return None
