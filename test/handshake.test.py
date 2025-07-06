#!/usr/bin/env python3
import os, sys, time, signal, subprocess, requests, contextlib

# ───── مسیرها
BASE = os.path.abspath(os.path.join(__file__, "..", ".."))
SRV  = os.path.join(BASE, "server")
XRAY = os.path.join(SRV,  "xray")
CFG  = os.path.join(SRV,  "config", "vless-cloudflare.json")

PORT        = 10808
TEST_URL    = "https://www.gstatic.com/generate_204"
START_TMO   = 12        # ثانیه
RETRY_WAIT  = 0.5       # بین تلاش‌ها
RETRY_MAX   = 5         # چند بار تست کنیم

# ───── آیا پراکسی آماده است؟
def proxy_ok() -> bool:
    p = {"http": f"socks5h://127.0.0.1:{PORT}",
         "https":f"socks5h://127.0.0.1:{PORT}"}
    try:
        r = requests.get(TEST_URL, proxies=p, timeout=8)
        return r.status_code in (200, 204)
    except Exception:
        return False

# ───── کانتکست: بالا/پایین کردن Xray
@contextlib.contextmanager
def ensure_xray():
    proc = None
    env  = os.environ.copy()
    env["XRAY_LOCATION_ASSET"] = SRV             # ← نقطه‌ی فایل‌های Geo
    if not proxy_ok():                           # فقط اگر خاموش است
        proc = subprocess.Popen(
            [XRAY, "run", "-config", CFG],
            cwd=SRV, env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        deadline = time.time() + START_TMO
        for line in proc.stdout:
            if "started" in line.lower(): break
            if "failed"  in line.lower() or time.time() > deadline:
                proc.kill(); raise RuntimeError("Xray failed to start.")
    try:
        yield
    finally:
        if proc and proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try: proc.wait(timeout=3)
            except: proc.kill()

# ───── اجرای هندشیک
def main():
    with ensure_xray():
        for _ in range(RETRY_MAX):
            if proxy_ok():
                print("true"); sys.exit(0)
            time.sleep(RETRY_WAIT)
    print("false"); sys.exit(1)

if __name__ == "__main__":
    import time
    main()
