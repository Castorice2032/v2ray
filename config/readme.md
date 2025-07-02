## بخش «کانفیگ» – دستورالعمل تست و پایش اتصال سرور

> این راهنما توضیح می‌دهد چگونه با استفاده از **یک فایل پیکربندی واحد** (مثلاً `config.json`) اتصال هر سرور را تست و در صورت نیاز به‌طور خودکار پایش کنید.

---

### ۱) پیش‌نیازها

* Xray (یا forkهای سازگار مانند sing-box) **نسخه ≥ v1.8** نصب باشد.
* فایل پیکربندی‌‌ای که تگ‌های `outbound`‌ در آن به‌درستی تعریف شده‌اند (نمونهٔ کامل در همین مخزن موجود است).

---

### ۲) پیدا کردن تگ خروجی (Outbound Tag)

در بخش `outbounds` کانفیگ، تگ سروری را که می‌خواهید تست کنید پیدا کنید. مثال:

```json5
{
  "tag": "vmess-tcp-tls",
  "protocol": "vmess",
  ...
}
```

> مقدار `tag` («vmess-tcp-tls») همان چیزی است که در فرمان تست استفاده می‌شود.

---

### ۳) تست سریع با دستور داخلی Xray

```bash
xray run -test \
  -config ./config.json \
  -outboundTag vmess-tcp-tls \
  -dest google.com:80
```

پارامترها:

* `-config` : مسیر فایل کانفیگ.
* `-outboundTag` : تگ گامِ قبل.
* `-dest` : هاست و پورت مقصد برای برقراری TCP (برای UDP پارامتر `-protocol udp`).

#### نمونهٔ خروجی موفق

```text
[Info]  tcp: google.com:80 → vmess-tcp-tls ... [OK] 56ms
```

#### نمونهٔ شکست

```text
[Error] tcp: dial tcp HANDSHAKE failed → timeout
```

---

### ۴) تست دسترسی پورت (TCP Ping)

اگر می‌خواهید صرفاً ببینید فایروالِ مسیر پورت را نمی‌بندد:

```bash
tcping <SERVER_IP_OR_DOMAIN> 443
```

---

### ۵) پینگ ICMP (در صورت باز بودن)

```bash
ping <SERVER_IP>
```

> اگر سرور ICMP را بسته باشد، تایم‌اوت به معنای قطع سرویس نیست؛ نتیجهٔ `xray -test` معتبرتر است.

---

### ۶) پایش خودکار سلامت مسیر (اختیاری)

برای اینکه Xray هر چند دقیقه یک‌بار مسیر را چک کرده و در صورت اختلال، تگ جایگزین را فعال کند، قطعهٔ زیر را به فایل اضافه کنید:

```json5
{
  "observatory": {
    "outbounds": [
      {
        "tag": "vmess-tcp-tls",
        "interval": "5m",
        "url": "https://cp.cloudflare.com/generate_204"
      }
    ]
  }
}
```

* `interval` : فاصلهٔ زمانی بین تست‌ها (مثلاً "5m" یعنی هر ۵ دقیقه).
* `url` : مقصدی که باید کد پاسخ ‎`204` بدهد (برای تست دسترسی اینترنت واقعی است).

---

### ۷) نکته‌ها و رفع خطا

* **TLS/Reality** : اگر از TLS یا Reality استفاده می‌کنید، اطمینان حاصل کنید فیلدهای `serverName`, `publicKey`, `shortId` در کانفیگ درست وارد شده باشند؛ در غیر این صورت handshake شکست می‌خورد.
* **فاصلهٔ زمانی زیاد** : در کانکشن‌های ماهواره‌ای یا شبکه‌های با تأخیر بالا، ممکن است نیاز باشد مقدار `timeout` Xray را افزایش دهید.
* **سرویس‌های مختلف، پورت‌های یکسان** : در صورتی که چند سرویس روی یک پورت اجرا می‌شوند، تست را با دامنه یا مسیر درست (`ws path`, `grpc serviceName`) انجام دهید.

---

### ۸) اسکریپت مانیتور همهٔ VLESS‌ها (ثبت نتیجه در لاگ)

اگر چند `outbound` با پروتکل VLESS دارید و می‌خواهید وضعیت هرکدام را در یک لاگ ببینید، اسکریپت زیر را در کنار `config.json` ذخیره کرده و روی کران اجرا کنید:

```bash
#!/usr/bin/env bash
CONFIG=./config.json        # مسیر فایل کانفیگ
DEST="cp.cloudflare.com:80" # مقصد تست (HTTP 204)

jq -r '.outbounds[] | select(.protocol=="vless") | .tag' "$CONFIG" | \
while read -r TAG; do
  RESULT=$(xray run -test -config "$CONFIG" -outboundTag "$TAG" -dest "$DEST" 2>&1)
  STATUS=$(echo "$RESULT" | grep -q "\[OK\]" && echo "OK" || echo "FAIL")
  RTT=$(echo "$RESULT" | grep -oE '[0-9]+ms' || echo "-")
  printf '%-20s %-4s %s
' "$TAG" "$STATUS" "$RTT"
done | tee -a vless_health.log
```

* **jq** برای استخراج تگ‌ها از JSON لازم است (`sudo apt install jq`).
* خروجی روی صفحه و همزمان در فایل `vless_health.log` ذخیره می‌شود.
* از کران‌تب می‌توانید هر ۵ دقیقه آن را اجرا کنید:

  ```bash
  */5 * * * * /path/to/vless_check.sh
  ```

---

### ۹) راه‌اندازی پایش داخلی با Observatory (گزینهٔ بدون اسکریپت)

اگر ترجیح می‌دهید همه‌چیز داخل Xray باشد، کافی است در بخش ریشهٔ کانفیگ، ماژول `observatory` را اضافه کنید و برای هر تگ VLESS یک آیتم بنویسید:

```json5
"observatory": {
  "outbounds": [
    {
      "tag": "vless-grpc-reality-1",
      "interval": "5m",
      "url": "https://cp.cloudflare.com/generate_204"
    },
    {
      "tag": "vless-grpc-reality-2",
      "interval": "5m",
      "url": "https://cp.cloudflare.com/generate_204"
    }
  ]
}
```

* پس از افزودن این بخش، Xray هنگام اجرا RTT و خطاهای handshake هر سرور VLESS را در لاگ خود ثبت می‌کند؛ می‌توانید با `journalctl -u xray -f` آن را رصد کنید.
* اگر در `routing` شما بالانسر تعریف شده باشد، Xray می‌تواند به‌طور خودکار سرورهای **FAILED** را موقتاً کنار بگذارد.

---

### ۱۰) ساخت فایل‌های Outbound مجزا (confdir)

اگر می‌خواهید هر دسته تنظیم (مثلاً همهٔ `outbound`‌ها) را در فایل جداگانه نگه دارید:

1. **ساخت پوشهٔ کانفیگ** – مثلاً `configs/`.
2. **انتقال فایل اصلی** به `configs/root.json` (یا نام دلخواه).
3. **ایجاد فایل فقط برای خروجی‌ها**، مثلاً `configs/outbounds.json` با محتوی زیر:

   ```json5
   {
     "outbounds": [
       {
         "tag": "vless-1",
         "protocol": "vless",
         "settings": { /* … */ },
         "streamSettings": { /* … */ }
       },
       {
         "tag": "vless-2",
         "protocol": "vless",
         "settings": { /* … */ },
         "streamSettings": { /* … */ }
       }
     ]
   }
   ```
4. **اجرای Xray با پوشه به‌جای فایل**:

   ```bash
   xray run -confdir ./configs
   ```

   * Xray همهٔ فایل‌های ‎`.json` داخل پوشه را لود کرده و مقادیر را Merge می‌کند.

> **فرمت** هر فایل باید JSON خالص باشد (بدون ‎`//` و ‎`/* … */` در نسخهٔ رسمی). اگر نیاز به کامنت دارید از ‎`.jsonc` یا ابزارهایی مثل `xray --format=json` برای تبدیل استفاده کنید.

---

### TL;DR

۱. برای تست تکی: `xray run -test -config config.json -outboundTag <TAG> -dest google.com:80`
۲. برای مانیتور گروهی VLESS: از اسکریپت بخش ۸ + کران استفاده کنید.
۳. یا با افزودن `observatory` (بخش ۹) پایش را داخل خود Xray بسپارید.
