import logging
import sys
from pathlib import Path

# افزودن دایرکتوری اصلی پروژه به sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from logs.log import LoggerManager

# دریافت لاگر با نام ماژول فعلی
logger = LoggerManager.get_logger(__name__, level=logging.DEBUG)

def test_logging():
    # تست لاگ‌های مختلف
    logger.debug("این یک پیام DEBUG است برای تست جزئیات.")
    logger.info("این یک پیام INFO است برای اطلاعات عمومی.")
    logger.warning("این یک پیام WARNING است برای هشدار.")
    logger.error("این یک پیام ERROR است برای خطاها.")
    try:
        # شبیه‌سازی یک خطا
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.exception("یک استثنا رخ داد: %s", e)

if __name__ == "__main__":
    print("شروع تست لاگ‌گذاری...")
    test_logging()
    print("تست لاگ‌گذاری تکمیل شد. فایل project.log را در دایرکتوری اصلی پروژه بررسی کنید.")