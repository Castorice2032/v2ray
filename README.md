"""
ادغام، پالایش و گروه‌بندی داینامیک سابسکریپشن‌های Clash از طریق Subconverter
Author: ChatGPT (o3)

ویژگی‌ها
--------
1. خواندن لیست URL-ها از فایل «urls.txt» (هر خط یک آدرس؛ خط خالی یا کامنت # نادیده گرفته می‌شود)
2. دریافت خروجی Clash به‌وسیلهٔ Subconverter
3. فیلتر نودهای خراب (UUID یا cipher نامعتبر، هدر h2/grpc بدون TLS و...)
4. تست اتصال TCP سریع (۲ ثانیه) برای جداسازی نودهای دسترس‌پذیر (Alive) از نودهای غیردسترس (Dead)
5. ساخت گروه‌های:
   • Alive  (url-test روی نودهای سالم)
   • Dead   (select، صرفاً برای بررسی دستی)
   • GLOBAL (select شامل Alive و—اگر وجود داشت—Dead)
6. نوشتن نتیجه در «merged_clean.yaml» ــ آمادهٔ ایمپورت در Clash

پیش‌نیازها
----------
pip install requests pyyaml
(Subconverter در حال اجرا روی 127.0.0.1:25500 یا آدرس دلخواه)
"""




# فرض: Subconverter روی 127.0.0.1:25500 در حال اجراست
python clean_merge_subconverter.py -o my_config.yaml

python app.py \
  -u urls.txt \
  -o my_config.yaml

python clean_merge_subconverter.py \
  -s http://[<VPS-IP>](https://improved-giggle-q7xvg4997wv5f4pq6-25500.app.github.dev/):25500 \
  -u urls.txt \
  -o my_config.yaml




  chanel api : 7787890538:AAHFg5Lpgz7byfR461jyoPY7W6P9bYmnMNU
  chanel id : @netnestvpn