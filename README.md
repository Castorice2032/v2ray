"""
# v2ray Proxy Tools

ابزارهای مدیریت، پالایش و آنالیز سابسکریپشن‌های پروکسی (Clash, V2Ray, Hysteria2 و ...)

---

## ساختار پروژه و مسئولیت فایل‌های مهم

- **urls.txt**: لیست URL سابسکریپشن‌ها (هر خط یک آدرس)
- **requirements.txt**: لیست پکیج‌های مورد نیاز پایتون
- **main.py**: نقطه شروع یا اسکریپت اصلی (در صورت وجود)
- **convert_and_test.py**: تبدیل و تست کانفیگ‌ها
- **sing-box.py**: تست وضعیت سرور با استفاده از sing-box (پشتیبانی از Hysteria2 و ...)
- **server_analyzer.py**: آنالیز و تست سرورهای پروکسی (پینگ، TCP، TLS)
- **backup/app.py**: ادغام و پالایش سابسکریپشن‌ها با Subconverter و ساخت yaml نهایی
- **backup/clean_merge_subconverter.py**: پالایش و ادغام پیشرفته سابسکریپشن‌ها
- **utils/**: ابزارهای جانبی (استخراج، آنالیز، ارسال تلگرام و ...)
- **data/**: داده‌های خروجی و ورودی (input, logs, output)
- **config/config.json**: نمونه کانفیگ برای کلاینت Xray/V2Ray
- **hysteria2.json**: نمونه کانفیگ Hysteria2
- **index.html**: رابط کاربری ساده وب (برای تلگرام)

---

## ویژگی‌ها

1. خواندن لیست URL-ها از فایل `urls.txt` (هر خط یک آدرس؛ خط خالی یا کامنت # نادیده گرفته می‌شود)
2. دریافت خروجی Clash به‌وسیلهٔ Subconverter
3. فیلتر نودهای خراب (UUID یا cipher نامعتبر، هدر h2/grpc بدون TLS و...)
4. تست اتصال TCP سریع (۲ ثانیه) برای جداسازی نودهای دسترس‌پذیر (Alive) از نودهای غیردسترس (Dead)
5. ساخت گروه‌های:
   - Alive  (url-test روی نودهای سالم)
   - Dead   (select، صرفاً برای بررسی دستی)
   - GLOBAL (select شامل Alive و—اگر وجود داشت—Dead)
6. نوشتن نتیجه در `merged_clean.yaml` ــ آمادهٔ ایمپورت در Clash
7. آنالیز و تست سرورها با `server_analyzer.py` و `sing-box.py`

---

## پیش‌نیازها

```bash
pip install -r requirements.txt
```

برای استفاده از Subconverter:
- Subconverter باید روی 127.0.0.1:25500 یا آدرس دلخواه اجرا شود.

---

## دستورات نمونه

### ادغام و پالایش سابسکریپشن‌ها
```bash
python backup/clean_merge_subconverter.py -o my_config.yaml
python backup/app.py -u urls.txt -o my_config.yaml
```

### آنالیز سرورها (پینگ، TCP، TLS)
```bash
python server_analyzer.py configs.txt report.json
```

### تست سرور با sing-box (مثلاً Hysteria2)
```bash
python sing-box.py hysteria2.json
```

---

## پوشه‌ها و فایل‌های مهم

- **backup/**: ابزارهای کمکی و اسکریپت‌های پالایش و ادغام
- **utils/**: ابزارهای استخراج و آنالیز
- **data/input/**: ورودی‌ها (لیست لینک‌ها)
- **data/logs/**: لاگ و گزارش خروجی
- **data/output/**: خروجی‌های نهایی
- **config/**: نمونه کانفیگ‌ها و مستندات

---

## توسعه‌دهنده
ChatGPT (o3) و مشارکت‌کنندگان
```


