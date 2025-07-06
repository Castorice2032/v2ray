import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import json, socket, ssl, http.client, time, ipaddress, subprocess, shutil, re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ───────────────────────────── Setup logging
logger = logging.getLogger("health_checker")
logger.setLevel(logging.DEBUG)
log_format = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
console = logging.StreamHandler()
console.setFormatter(log_format)
logger.addHandler(console)

# ───────────────────────────── Load protocol schema
# Locate protocol.json in project root config folder
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config" / "protocol.json"
try:
    PROTOCOLS: Dict[str, Dict[str, Any]] = json.loads(SCHEMA_PATH.read_text("utf-8"))
    logger.info(f"✅ Loaded protocol schema from {SCHEMA_PATH}")
except Exception as e:
    logger.error(f"❌ Failed to load protocol schema: {e}")
    raise

# ───────────────────────────── Nmap availability
NMAP_PATH = shutil.which("nmap")
if not NMAP_PATH:
    logger.warning("nmap not found in PATH, falling back to socket checks")

# ───────────────────────────── Helpers
def is_ip(addr: str) -> bool:
    try:
        ipaddress.ip_address(addr)
        return True
    except ValueError:
        return False

def resolve_host(host: str) -> Optional[str]:
    if is_ip(host):
        return host
    try:
        ip = socket.gethostbyname(host)
        logger.debug(f"Resolved {host} → {ip}")
        return ip
    except Exception as e:
        logger.warning(f"DNS resolution failed for {host}: {e}")
        return None

# ───────────────────────────── Checkers
def tcp_check(host: str, port: int, timeout: float, **_) -> bool:
    """Use nmap TCP scan if available, else fallback to socket."""
    if NMAP_PATH:
        cmd = [NMAP_PATH, "-Pn", "-p", str(port), host]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=timeout+5)
            # match lines like 'PORT STATE SERVICE'
            match = re.search(rf"{port}/tcp\s+open", out)
            return bool(match)
        except Exception:
            return False
    # fallback
    with socket.create_connection((host, port), timeout):
        return True

def tls_check(host: str, port: int, timeout: float, server_name: Optional[str] = None, **_) -> bool:
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(socket.create_connection((host, port), timeout), server_hostname=server_name or host):
        return True

def ws_check(host: str, port: int, timeout: float, use_tls=False, path="/", headers=None, **_) -> bool:
    conn_cls = http.client.HTTPSConnection if use_tls else http.client.HTTPConnection
    conn = conn_cls(host, port, timeout=timeout)
    try:
        conn.request("GET", path, headers=headers or {})
        conn.getresponse()
        return True
    finally:
        conn.close()

def udp_check(host: str, port: int, timeout: float, payload=b"", expect_reply=False, **_) -> bool:
    # Use nmap UDP scan if available
    if NMAP_PATH:
        cmd = [NMAP_PATH, "-Pn", "-sU", "-p", str(port), host]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=timeout+5)
            match = re.search(rf"{port}/udp\s+open", out)
            return bool(match)
        except Exception:
            return False
    # fallback to socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(payload, (host, port))
        if expect_reply:
            sock.recv(1)
        return True
    finally:
        sock.close()

CHECKERS: Dict[str, Callable[..., bool]] = {
    "tcp_check": tcp_check,
    "tls_check": tls_check,
    "ws_check": ws_check,
    "udp_check": udp_check,
}

def vmess_check(host, port, timeout, transport="tcp", path="/", tls=False, headers=None, **_) -> bool:
    if transport in ("ws", "ws+tls"):
        return ws_check(host, port, timeout, use_tls=tls or transport.endswith("+tls"), path=path, headers=headers)
    return tls_check(host, port, timeout) if tls else tcp_check(host, port, timeout)

CHECKERS["vmess_check"] = vmess_check

# ───────────────────────────── Core checker
def check_node(node: Dict[str, Any], timeout_default=3.0) -> Dict[str, Any]:
    cfg = node.get("config", {})
    proto = (cfg.get("type") or node.get("type") or "").lower()
    host = cfg.get("server")
    port = cfg.get("port")

    if not host or not port:
        logger.error(f"[{proto}] missing host/port")
        return {"ok": False, "reason": "missing_host_or_port"}

    schema = PROTOCOLS.get(proto)
    if not schema:
        logger.error(f"[{proto}] unsupported protocol")
        return {"ok": False, "reason": f"unknown_protocol:{proto}"}

    timeout = cfg.get("timeout") or schema.get("timeout") or timeout_default
    ip = resolve_host(host)
    if not ip:
        return {"ok": False, "reason": "resolve_failed", "host": host, "port": port}

    checker_name = schema["checker"]
    checker = CHECKERS.get(checker_name)
    if not checker:
        logger.error(f"[{proto}] missing checker '{checker_name}'")
        return {"ok": False, "reason": f"checker_not_found:{checker_name}", "host": host}

    # Extra args
    extra: Dict[str, Any] = {}
    transport = cfg.get("transport", {}).get("type", schema.get("transports", [None])[0])
    if transport:
        extra["transport"] = transport
        extra["path"] = cfg.get("transport", {}).get("path", "/")
        extra["headers"] = cfg.get("transport", {}).get("headers")
        extra["tls"] = transport.endswith("+tls")

    if checker_name == "udp_check":
        payload_cfg = cfg.get("udp_payload") or schema.get("udp_payload", "")
        if payload_cfg.startswith("0x"):
            extra["payload"] = bytes.fromhex(payload_cfg[2:])
        else:
            extra["payload"] = payload_cfg.encode()
        extra["expect_reply"] = schema.get("udp_expect_reply", False)

    if schema.get("tls_supported"):
        extra["tls"] = extra.get("tls") or cfg.get("tls", {}).get("enabled", False)

    try:
        start = time.time()
        ok = checker(host, port, timeout, **extra)
        latency = int((time.time() - start) * 1000)
        logger.info(f"[{proto}] ✅ {host}:{port} ({latency}ms)")
        node.setdefault("meta", {})["latency_ms"] = latency
        return {"ok": True, "host": host, "ip": ip, "port": port, "latency_ms": latency}
    except Exception as e:
        logger.warning(f"[{proto}] ❌ {host}:{port} → {e}")
        return {"ok": False, "host": host, "ip": ip, "port": port, "reason": str(e)}

# ───────────────────────────── Parallel execution
def health_check_nodes(nodes: List[Dict[str, Any]], max_workers=20) -> List[Dict[str, Any]]:
    results: Dict[int, Dict[str, Any]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {executor.submit(check_node, node): i for i, node in enumerate(nodes)}
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                results[i] = future.result()
            except Exception as e:
                logger.error(f"Unhandled error in thread {i}: {e}")
                results[i] = {"ok": False, "reason": "unexpected_error"}

    # حفظ ترتیب
    return [results[i] for i in range(len(nodes))]

# ───────────────────────────── CLI demo
if __name__ == "__main__":
    sample_nodes = [
        {"config": {"server": "example.com", "port": 443, "type": "trojan", "tls": {"enabled": True}}},
        {"config": {"server": "1.1.1.1", "port": 443, "type": "hysteria2", "udp_payload": "0x50494E47"}},
    ]
    final = health_check_nodes(sample_nodes)
    for node in final:
        print(json.dumps(node, ensure_ascii=False, indent=2))
