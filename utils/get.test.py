

# فراخوانی تابع دریافت ستون config از جدول proxy_nodes
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parent / "utils"))
import importlib.util
import json
import subprocess
import socket
db_get_path = str(Path(__file__).resolve().parent / "db-get.py")
spec = importlib.util.spec_from_file_location("db_get", db_get_path)
db_get = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_get)

def resolve_to_ip(host):
    try:
        ip = socket.gethostbyname(host)
        return ip
    except Exception as e:
        print(f"[!] خطا در تبدیل {host} به IP: {e}")
        return host

def nmap_ping(server, port):
    ip = resolve_to_ip(server)
    status = "unknown"
    protocol = "tcp"
    port_open = False
    udp_available = False
    try:
        # بررسی TCP
        result_tcp = subprocess.run([
            "nmap", "-Pn", "-p", str(port), ip
        ], capture_output=True, text=True, timeout=10)
        lines_tcp = result_tcp.stdout.splitlines()
        port_status = ""
        for line in lines_tcp:
            if f"{port}/tcp" in line:
                port_status = line.strip()
                if "open" in port_status:
                    port_open = True
                break
        # بررسی UDP
        result_udp = subprocess.run([
            "nmap", "-sU", "-Pn", "-p", str(port), ip
        ], capture_output=True, text=True, timeout=10)
        lines_udp = result_udp.stdout.splitlines()
        for line in lines_udp:
            if f"{port}/udp" in line and "open" in line:
                udp_available = True
                break
        # تعیین وضعیت
        if port_open:
            status = "up"
        elif not port_open and not udp_available:
            status = "down"
        else:
            status = "unknown"
        return ip, port_open, udp_available, status
    except Exception as e:
        print(f"[!] Nmap error for {server}:{port}: {e}")
        return ip, False, False, "unknown"

def ping_host(ip):
    try:
        # ارسال 3 پینگ و محاسبه میانگین
        result = subprocess.run([
            "ping", "-c", "3", ip
        ], capture_output=True, text=True, timeout=10)
        lines = result.stdout.splitlines()
        for line in lines:
            if "avg" in line or "rtt min/avg/max" in line:
                # برای لینوکس: rtt min/avg/max/mdev = 0.123/0.234/0.345/0.045 ms
                parts = line.split("=")[-1].split("/")
                if len(parts) >= 2:
                    return parts[1].strip()
        return "-"
    except Exception as e:
        return f"خطا: {e}"

def print_server_port_and_ping():
    conn = db_get.psycopg2.connect(db_get.DB_URL)
    cur = conn.cursor()
    query = 'SELECT config FROM "proxy_nodes" ORDER BY created_at DESC LIMIT 10'
    cur.execute(query)
    rows = cur.fetchall()
    print("\n--- نتایج سرورها ---")
    for row in rows:
        try:
            config = row[0]
            if isinstance(config, str):
                config = json.loads(config)
            server = config.get("server")
            port = config.get("port")
            if server and port:
                ip, port_open, udp_available, status = nmap_ping(server, port)
                ping_result = "-"
                if status == "up":
                    ping_result = ping_host(ip)
                print(f"{server}:{port} | protocol: tcp{'/udp' if udp_available else ''} | status: {status} | ping: {ping_result}")
            else:
                print(f"[!] داده ناقص: {config}")
        except Exception as e:
            print(f"[!] Error parsing config: {e}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    print_server_port_and_ping()
