"""
Modular ping utilities for single and batch host reachability tests.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess, shutil, socket
from typing import List, Dict, Any
import logging

# Locate tcping
TCPING_PATH = shutil.which("tcping")
if not TCPING_PATH:
    logging.getLogger(__name__).warning("tcping not found in PATH, defaulting to ICMP ping")


def ping_host(host: str, count: int = 1, timeout: int = 1, port: int = 80) -> bool:
    """Ping a host using tcping (TCP ping) if available, else ICMP ping."""
    # Try tcping if available
    if TCPING_PATH:
        cmd = [TCPING_PATH, host, str(port), "-c", str(count), "-t", str(timeout)]
        try:
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=count * (timeout + 1))
            return result.returncode == 0
        except Exception:
            # Fall through to socket check
            pass
    # Fallback to TCP socket connection check
    for _ in range(count):
        try:
            with socket.create_connection((host, port), timeout):
                return True
        except Exception:
            continue
    return False

def ping_hosts(hosts: List[str], count: int = 1, timeout: int = 1, port: int = 80, concurrency: int = 10) -> List[Dict[str, Any]]:
    """Check multiple hosts concurrently, return list of statuses."""
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_host = {executor.submit(ping_host, host, count, timeout, port): host for host in hosts}
        for future in as_completed(future_to_host):
            host = future_to_host[future]
            try:
                ok = future.result()
            except Exception:
                ok = False
            results.append({"host": host, "reachable": ok})
    return results

__all__ = ["ping_host", "ping_hosts"]