"""
Simplified health checking API for proxy node configurations.
Provides functions for IP checks, connectivity tests, and batch health scans.
"""

# Package exports

# Expose simplified health API from health.py
from .health import (
    is_ip, resolve_host,
    tcp_check, tls_check, ws_check, udp_check, vmess_check,
    check_node, health_check_nodes
)
from .ping import ping_host, ping_hosts
from .region import get_country, ensure_geolite_db
from .validator import validate_config, validate_configs

__all__ = [
    "is_ip", "resolve_host",
    "tcp_check", "tls_check", "ws_check", "udp_check", "vmess_check",
    "check_node", "health_check_nodes"
    , "ping_host", "ping_hosts"
    , "get_country", "ensure_geolite_db", "validate_config", "validate_configs"
]
