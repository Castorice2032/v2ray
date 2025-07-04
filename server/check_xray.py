#!/usr/bin/env python3
"""
ss_handshake_check.py  →  true/false اگر هندشیک Shadowsocks موفق باشد.
"""
import subprocess, requests, time, signal, sys, tempfile, json, os, pathlib

XRAY_BIN = "./xray"             # یا مسیر مطلق
TEST_URL = "https://www.gstatic.com/generate_204"  # کوچک و سریع

CLIENT_JSON = {
    "log": { "loglevel": "debug", "access": "/dev/stdout", "error": "/dev/stderr" },
    "inbounds": [{ "listen": "127.0.0.1", "port": 2080, "protocol": "socks", "settings": {} }],
    "outbounds": [{
        "protocol": "shadowsocks",
        "settings": { "servers": [{
            "address": "127.0.0.1",         #← اینجا IP یا دامنهٔ سرور واقعی
            "port":    46106,
            "method":  "chacha20-ietf-poly1305",
            "password":"q4KN4QDZs5bCmj1LM8lFthy3Jmi+kr5bMoirUWrUkKs="
        }] }
    }]
}

def run_check(cfg: dict) -> bool:
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        json.dump(cfg, f); f.flush()
        proc = subprocess.Popen(
            [XRAY_BIN, "run", "-config", f.name],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        # صبر تا Xray بالا بیاید
        started = False; deadline = time.time() + 10
        for line in proc.stdout:
            if "started" in line.lower(): started = True; break
            if "failed"  in line.lower(): proc.kill(); return False
            if time.time() > deadline:   proc.kill(); return False

        if not started:
            proc.kill(); return False

        # حالا یک درخواست از طریق SOCKS‌ می‌فرستیم
        proxies = {"http": "socks5h://127.0.0.1:2080",
                   "https":"socks5h://127.0.0.1:2080"}
        try:
            r = requests.get(TEST_URL, proxies=proxies, timeout=8)
            ok = r.status_code in (200,204)
        except Exception:
            ok = False
        finally:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=5)

    os.remove(f.name)
    return ok

if __name__ == "__main__":
    print("true" if run_check(CLIENT_JSON) else "false")
    sys.exit(0 if run_check(CLIENT_JSON) else 1)
