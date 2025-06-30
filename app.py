#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py – دانلود/راه‌اندازی Subconverter (در صورت نبود)،
ادغام و پالایش سابسکریپشن، تست TCP همزمان، ساخت merged_clean.yaml.
پیش‌نیاز:  pip install requests pyyaml
"""

import os, sys, re, yaml, time, stat, shutil, socket, argparse, platform, subprocess, requests, tarfile, zipfile
from pathlib import Path
from urllib.parse import quote_plus
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ───── ثابت‌ها
SUB_PORT, SUB_URL = 25500, "http://127.0.0.1:25500"
BIN_DIR = Path(".subconv"); BIN_DIR.mkdir(exist_ok=True)
ALLOWED_SS_CIPHERS = {"aes-128-gcm","aes-192-gcm","aes-256-gcm","chacha20-ietf-poly1305"}
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

# ───── ابزار
def tcp_ok(host:str, port:int, timeout=2.0)->bool:
    try:  # noqa: E722
        with socket.create_connection((host, port), timeout): return True
    except: return False
def uid_ok(v): return bool(UUID_RE.fullmatch(v.strip()))
def port_ok(p): return str(p).isdigit() and 0<int(p)<65536

# ───── راه‌اندازی Subconverter
def ensure_subconverter():
    if tcp_ok("127.0.0.1", SUB_PORT, 1):
        print("[✓] Subconverter در حال اجراست."); return

    print("[!] Subconverter یافت نشد؛ دانلود و اجرا …")
    sys_os = "windows" if platform.system().lower().startswith("win") else "linux"
    asset = "subconverter_windows.zip" if sys_os=="windows" else "subconverter_linux64.tar.gz"
    url   = f"https://github.com/tindy2013/subconverter/releases/latest/download/{asset}"
    zf    = BIN_DIR/asset
    if not zf.exists():
        print("⤵️  دانلود:", url)
        with requests.get(url, stream=True, timeout=120) as r: r.raise_for_status(); zf.write_bytes(r.content)
    print("📦 استخراج …")
    if asset.endswith(".tar.gz"):  tarfile.open(zf,"r:gz").extractall(BIN_DIR)
    else:                          zipfile.ZipFile(zf).extractall(BIN_DIR)
    exe = next(BIN_DIR.rglob("subconverter.exe" if sys_os=="windows" else "subconverter"))
    os.chmod(exe, 0o755)
    print("🚀 اجرا …")
    if sys_os=="windows":
        subprocess.Popen([str(exe)], creationflags=subprocess.DETACHED_PROCESS)
    else:
        subprocess.Popen([str(exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(15):
        if tcp_ok("127.0.0.1", SUB_PORT, 1):
            print("[✓] Subconverter آماده است."); return
        time.sleep(1)
    sys.exit("⛔ Subconverter بالا نیامد!")

# ───── اعتبار نود
def node_valid(n:dict)->bool:
    t=str(n.get("type","")).lower()
    if t in {"vmess","vless"}:
        if not (uid_ok(n.get("uuid","")) and port_ok(n.get("port"))): return False
        if str(n.get("network","")).lower() in {"h2","grpc"} and not n.get("tls",True): return False
        return True
    if t=="trojan":
        return all(n.get(k) for k in("server","port","password")) and port_ok(n["port"])
    if t=="ss":
        return n.get("cipher") in ALLOWED_SS_CIPHERS and port_ok(n.get("port"))
    return False

# ───── دریافت YAML
def fetch_yaml(urls:list[str])->str:
    qs="&".join(f"{k}={quote_plus(v)}" for k,v in {
        "target":"clash","url":"|".join(urls),"udp":"true",
        "sort":"true","emoji":"true","list":"false"}.items())
    full=f"{SUB_URL}/sub?{qs}"
    print("⇢ درخواست:",full)
    r=requests.get(full,timeout=90); r.raise_for_status(); return r.text

# ───── ساخت کانفیگ با تست همزمان
def build(proxies):
    alive, dead, cnt = [], [], defaultdict(int)
    print(f"[INFO] تست TCP همزمان ({len(proxies)} نود)…")
    def task(p): return p, tcp_ok(p["server"], int(p["port"]), 2)
    with ThreadPoolExecutor(max_workers=40) as pool:
        futs=[pool.submit(task,p) for p in proxies if node_valid(p)]
        total=len(futs)
        for i,f in enumerate(as_completed(futs),1):
            p,ok=f.result()
            base=p["name"]; cnt[base]+=1
            if cnt[base]>1: p["name"]=f"{base} ({cnt[base]})"
            (alive if ok else dead).append(p)
            if i%20==0 or i==total: print(f"  … {i}/{total} تست شد")
    if not alive: sys.exit("⛔ Alive پیدا نشد!")
    groups=[
        {"name":"Alive","type":"url-test","url":"http://www.gstatic.com/generate_204",
         "interval":300,"proxies":[x["name"] for x in alive]}
    ]
    if dead: groups.append({"name":"Dead","type":"select","proxies":[x["name"] for x in dead]})
    groups.append({"name":"GLOBAL","type":"select","proxies":["Alive"]+(["Dead"] if dead else [])+["DIRECT"]})
    return alive+dead, groups

# ───── main
def main(urlfile, output):
    ensure_subconverter()
    urls=[u.strip() for u in Path(urlfile).read_text(encoding="utf-8").splitlines()
          if u.strip() and not u.startswith("#")]
    if not urls: sys.exit("urls.txt خالی است.")
    data=yaml.safe_load(fetch_yaml(urls))
    merged,groups=build(data.get("proxies",[]))
    data["proxies"],data["proxy-groups"],data["rules"]=merged,groups,["MATCH,GLOBAL"]
    Path(output).write_text(yaml.dump(data,allow_unicode=True,sort_keys=False),encoding="utf-8")
    print(f"✅ {output} ساخته شد (Alive={len(groups[0]['proxies'])})")

# ───── CLI
if __name__=="__main__":
    ap=argparse.ArgumentParser(description="Clash subscription builder (concurrent TCP test)")
    ap.add_argument("-u","--urls",default="urls.txt",help="فایل URL ها")
    ap.add_argument("-o","--output",default="merged_clean.yaml",help="نام YAML خروجی")
    args=ap.parse_args()
    main(args.urls,args.output)
