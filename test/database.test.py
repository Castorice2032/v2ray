import sys
from pathlib import Path
import psycopg2

# افزودن دایرکتوری اصلی پروژه به sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.database import DatabaseManager

def test_database():
    try:
        with DatabaseManager() as db:
            # دریافت لیست جدول‌ها و تعداد ردیف‌ها
            print("\n--- لیست جدول‌ها و تعداد ردیف‌ها ---")
            db.cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = db.cur.fetchall()
            for table in tables:
                table_name = table[0]
                db.cur.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
                count = db.cur.fetchone()[0]
                print(f"جدول: {table_name} | تعداد ردیف‌ها: {count}")

            # دریافت 10 نتیجه آخر از جدول proxy_nodes
            print("\n--- 10 نتیجه آخر از جدول proxy_nodes ---")
            results = db.get(table="proxy_nodes", limit=10)
            if results:
                for row in results:
                    print(row)
            else:
                print("جدول proxy_nodes خالی است یا وجود ندارد.")

    except Exception as e:
        print(f"خطا در تست دیتابیس: {e}")

if __name__ == "__main__":
    print("شروع تست دیتابیس...")
    test_database()
    print("تست دیتابیس تکمیل شد. فایل project.log را بررسی کنید.")