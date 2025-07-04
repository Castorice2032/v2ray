"""
main.py - هسته مرکزی پروژه

این فایل نقطه ورود پروژه است و درخواست‌های کاربر را دریافت و به ماژول‌های مربوطه (مانند db.py) ارسال می‌کند.
"""
import sys
import json
from utils import db

def print_menu():
    print("""
    عملیات دیتابیس:
    1. نمایش نام جداول و تعداد رکوردها
    2. درج داده جدید (proxy_nodes)
    3. نمایش 10 رکورد آخر جدول proxy_nodes
    0. خروج
    """)

def main():
    while True:
        print_menu()
        cmd = input("انتخاب شما: ").strip()
        if cmd == "1":
            tables = db.get_tables_and_counts()
            for t, c in tables.items():
                print(f"جدول: {t} | تعداد رکورد: {c}")
        elif cmd == "2":
            print("یک یا چند نود را به صورت JSON وارد کنید (لیست دیکشنری):")
            data = input()
            try:
                nodes = json.loads(data)
                if not isinstance(nodes, list):
                    nodes = [nodes]
                db.insert_proxy_nodes(nodes)
                print("✅ داده‌ها با موفقیت درج شدند.")
            except Exception as e:
                print(f"❌ خطا در درج داده: {e}")
        elif cmd == "3":
            rows = db.get_all_proxy_nodes(limit=10)
            for row in rows:
                print(row)
        elif cmd == "0":
            print("خروج...")
            break
        else:
            print("دستور نامعتبر!")

if __name__ == "__main__":
    main()
