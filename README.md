"""
# v2ray Proxy Tools

ابزارهای مدیریت، پالایش و آنالیز سابسکریپشن‌های پروکسی (Clash, V2Ray, Hysteria2 و ...)

---

## ساختار پروژه و مسئولیت فایل‌های مهم

- **main.py**: نقطه شروع یا اسکریپت اصلی پروژه (در صورت وجود)
- **urls.txt**: لیست URL سابسکریپشن‌ها (هر خط یک آدرس)
- **requirements.txt**: لیست پکیج‌های مورد نیاز پایتون
- **index.html**: رابط کاربری ساده وب (برای تلگرام)
- **db-check.py**: بررسی وضعیت و اتصال دیتابیس
- **streamlit_app.py**: رابط گرافیکی برای مشاهده و مدیریت داده‌ها
- **backup/**: ابزارهای کمکی برای ادغام و پالایش سابسکریپشن‌ها
  - **app.py**: ادغام و پالایش سابسکریپشن‌ها با Subconverter و ساخت yaml نهایی
  - **clean_merge_subconverter.py**: پالایش و ادغام پیشرفته سابسکریپشن‌ها
  - **proxy/**: ابزارهای استخراج و گزارش‌گیری از لینک‌های پروکسی
  - **sources/**: ابزارهای تشخیص نوع لینک و مدیریت منابع
- **config/**: فایل‌های پیکربندی و شِما (db.json، schema.json و ...)
- **data/input/**: ورودی‌ها (لیست لینک‌ها و داده‌های خام)
- **data/json/**: خروجی‌های پردازش‌شده به فرمت JSON
- **data/logs/**: لاگ‌ها و گزارش‌های خطا و عملیات
- **data/tmp/**: فایل‌های موقت و داده‌های واسط
- **sing-box/**: ابزار و سورس کد تست سرور با sing-box (Go)
- **test/**: اسکریپت‌های تست و آنالیز
- **utils/**: ابزارهای جانبی و مدیریتی
  - **db.py**: لایه اصلی ارتباط با دیتابیس PostgreSQL؛ شامل توابع دریافت و درج داده (CRUD)
  - **db-get.py**: دریافت نام جداول و تعداد رکوردهای هر جدول از دیتابیس
---

## کار با دیتابیس (PostgreSQL)

### نکات کلیدی
- اطلاعات اتصال دیتابیس باید در فایل `.env` با یکی از کلیدهای `DATABASE_URL` یا `DB_URL` یا `POSTGRES_URL` قرار گیرد.
- ساختار جدول اصلی (مثلاً `proxy_nodes`) باید مطابق با شِمای پروژه باشد (ستون‌های id، type، config و ...).
- داده‌های json (مثل config) باید به صورت json یا jsonb ذخیره شوند.
- برای درج داده جدید، مقداردهی ستون‌های not null الزامی است.
- توابع ارتباط با دیتابیس همگی خروجی مناسب برای استفاده در سایر فایل‌ها دارند (return).

### توابع کلیدی در `utils/db.py`

- **get_column_data(table, column, limit=10)**: دریافت آخرین مقادیر یک ستون خاص از جدول
- **get_column_by_id(table, column, row_id)**: دریافت مقدار یک ستون خاص از یک ردیف خاص (بر اساس id)
- **get_row_by_id(table, row_id)**: دریافت همه ستون‌ها و مقادیر یک ردیف خاص (دیکشنری)
- **get_rows_by_type(table, type_value, limit=10)**: دریافت ردیف‌ها بر اساس مقدار type (مثلاً فقط سرورهای trojan)
- **insert_row(table, data_dict)**: درج یک ردیف جدید (داده‌ها به صورت دیکشنری)

#### مثال دریافت داده:
```python
from utils.db import get_column_data, get_row_by_id
# دریافت ۵ مقدار آخر ستون config
configs = get_column_data("proxy_nodes", "config", limit=5)
for c in configs:
    print(c)
# دریافت یک ردیف کامل بر اساس id
row = get_row_by_id("proxy_nodes", some_id)
print(row)
```

#### مثال درج داده:
```python
from utils.db import insert_row
import json
data = {
    "raw": "raw_test",
    "tag": "test_tag",
    "type": "trojan",
    "config": json.dumps({"server": "test.example.com", "port": 443}),
}
inserted_id = insert_row("proxy_nodes", data)
print("Inserted row id:", inserted_id)
```

#### مثال دریافت بر اساس type:
```python
from utils.db import get_rows_by_type
trojan_rows = get_rows_by_type("proxy_nodes", "trojan", limit=3)
for row in trojan_rows:
    print(row)
```

---

### نکات امنیتی و بهینه‌سازی
- همیشه از پارامترهای جایگزین (%s) برای جلوگیری از SQL Injection استفاده شده است.
- اتصال و cursor پس از هر عملیات بسته می‌شود.
- برای داده‌های json، قبل از درج باید json.dumps استفاده شود.
- برای دریافت داده‌های زیاد، از limit مناسب استفاده کنید.

---
  - **extract.py**: استخراج لینک‌ها از منابع مختلف
  - **telegram.py**: ارسال پیام و گزارش به تلگرام
  - **validation.py**: اعتبارسنجی داده‌ها و لینک‌ها

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


-la ~/server