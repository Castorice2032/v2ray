import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# بارگذاری env
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
DB_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or os.getenv("POSTGRES_URL")
if not DB_URL:
    print("❌ No database URL found in .env")
    exit(1)


# دریافت داده‌های یک ستون خاص از یک جدول خاص
def get_column_data(table_name, column_name, limit=10):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    query = f'SELECT {column_name} FROM "{table_name}" ORDER BY created_at DESC LIMIT %s'
    cur.execute(query, (limit,))
    rows = cur.fetchall()
    for row in rows:
        print(row[0])
    cur.close()
    conn.close()

# دریافت همه ستون‌ها و مقادیر یک ردیف خاص (بر اساس id)
def get_row_by_id(table_name, row_id):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    query = f'SELECT * FROM "{table_name}" WHERE id = %s'
    cur.execute(query, (row_id,))
    row = cur.fetchone()
    if row:
        colnames = [desc[0] for desc in cur.description]
        for col, val in zip(colnames, row):
            print(f"{col}: {val}")
    else:
        print("No row found with this id.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    # مثال: دریافت 10 مقدار آخر ستون config از جدول proxy_nodes
    get_column_data("proxy_nodes", "config", limit=10)

if __name__ == "__main__":
    get_tables_and_counts()