def update_region(node_id, region):
    """Update the region field for a proxy node by id."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('UPDATE proxy_nodes SET region=%s WHERE id=%s', (region, node_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
"""
db.py

This module is responsible for fast and parallel import of proxy node data into the PostgreSQL database table `proxy_nodes`.

Features:
---------
- Reads JSONL files containing lists of proxy nodes (e.g., all_nodes.jsonl).
- Performs batch and parallel insertion using ProcessPoolExecutor for high performance.
- Assumes data uniqueness (does not check for duplicates by default).
- Logs errors and import progress to the `data/logs` directory.
- Displays a progress bar for user feedback during import.
- Supports both parallel and sequential import modes.
- Designed for extensibility to support future requirements such as:
    - Receiving commands from higher-level layers (e.g., API or CLI).
    - Querying and retrieving information from the database.

Usage:
------
1. Place the desired JSONL file (e.g., data/tmp/all_nodes.jsonl) in the specified directory.
2. Run the script:
       python utils/db.py
3. To change the input file, modify the `jsonl_path` variable.

JSONL File Structure:
---------------------
Each line in the JSONL file must be a dictionary containing the required keys for the `proxy_nodes` table.

Environment:
------------
- Database connection details are loaded from a `.env` file (DATABASE_URL, DB_URL, or POSTGRES_URL).
- Requires the following Python packages: psycopg2, tqdm, python-dotenv.

Logging & Reporting:
--------------------
- Error logs are written to `data/logs/import_hysteria_jsonl.log`.
- Import summary reports are saved as JSON in `data/logs/import_report_hysteria_jsonl.json`.
- Duplicate entries (if checked) are logged in `data/logs/duplicate_all_nodes.log`.

Future Development:
-------------------
- Integration with higher-level layers for command reception and orchestration.
- Implementation of database query and retrieval functions for use by other modules or APIs.

Author: xoxxel
Last Modified: 1404/04/13 (2025-07-04)

"""
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import concurrent.futures

TMP_DIR = Path(__file__).resolve().parent.parent / "data/tmp"
LOG_DIR = Path(__file__).resolve().parent.parent / "data/logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


# --- Database Layer: Connection, Insert, Query ---
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
DB_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or os.getenv("POSTGRES_URL")
if not DB_URL:
    print("❌ No database URL found in .env")
    exit(1)

def get_connection():
    return psycopg2.connect(DB_URL)

def get_tables_and_counts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
    """)
    tables = [row[0] for row in cur.fetchall()]
    result = {}
    for table in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = cur.fetchone()[0]
        result[table] = count
    cur.close()
    conn.close()
    return result

def insert_proxy_nodes(nodes: list):
    """Insert a list of proxy node dicts into proxy_nodes table."""
    import uuid
    conn = get_connection()
    cur = conn.cursor()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for node in nodes:
        row = [
            str(uuid.uuid4()),
            node.get("raw"),
            node.get("tag"),
            node.get("type"),
            json.dumps(node.get("config")),
            None, None, "unknown", None, now, now
        ]
        rows.append(row)
    sql = '''INSERT INTO proxy_nodes (id, raw, tag, type, config, region, ping_ms, status, last_checked_at, created_at, updated_at)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
    try:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=100)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def get_all_proxy_nodes(limit=100):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f'SELECT id, raw, tag, type FROM proxy_nodes ORDER BY created_at DESC LIMIT %s', (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# --- تابع کمکی برای پردازش موازی (باید در سطح ماژول باشد) ---
def batch_insert_wrapper(args):
    batch, db_url = args
    return batch_insert_no_check(batch, db_url)

def import_hysteria_jsonl_parallel(jsonl_path, db_url, batch_size=1000, max_workers=4):
    from tqdm import tqdm
    import json
    nodes = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            node = json.loads(line)
            nodes.append(node)
    total = len(nodes)
    batches = [nodes[i:i+batch_size] for i in range(0, total, batch_size)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(
            executor.map(batch_insert_wrapper, [(batch, db_url) for batch in batches]),
            total=len(batches),
            desc="all_nodes.jsonl",
            ncols=80,
            colour='cyan'
        ))
    print(f"\n✅ all_nodes.jsonl import finished. Inserted: {total}")

# --- در انتهای فایل main را به شکل زیر تغییر دهید:
def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    summary = {}
    batch_size = 1000
    try:
        from tqdm import tqdm
    except ImportError:
        print("tqdm not found. Installing tqdm for progress bar...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
        from tqdm import tqdm

    # اپلود فایل all_nodes.jsonl به دیتابیس (بدون بررسی تکراری بودن)
    jsonl_path = Path(__file__).resolve().parent.parent / "data/tmp/all_nodes.jsonl"
    if not jsonl_path.exists():
        print(f"❌ File not found: {jsonl_path}")
        return
    from tqdm import tqdm
    import json
    nodes = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            node = json.loads(line)
            nodes.append(node)
    total = len(nodes)
    batch_size = 1000
    max_workers = 4
    batches = [nodes[i:i+batch_size] for i in range(0, total, batch_size)]
    inserted = 0
    log_path = LOG_DIR / "import_hysteria_jsonl.log"
    report_path = LOG_DIR / "import_report_hysteria_jsonl.json"
    errors = []
    def batch_insert_log(batch):
        try:
            batch_insert_no_check(batch, DB_URL)
            return len(batch), None
        except Exception as e:
            return 0, str(e)
    with tqdm(total=len(batches), desc="all_nodes.jsonl", ncols=80, colour='cyan') as pbar:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(batch_insert_log, batch) for batch in batches]
            for fut in concurrent.futures.as_completed(futures):
                count, err = fut.result()
                inserted += count
                if err:
                    errors.append(err)
                pbar.set_postfix(inserted=inserted, errors=len(errors))
                pbar.update(1)
    # Write error log if any
    if errors:
        with open(log_path, "w", encoding="utf-8") as logf:
            for err in errors:
                logf.write(str(err) + "\n")
    # Write summary report
    summary = {
        "total": total,
        "inserted": inserted,
        "errors": len(errors),
        "log": str(log_path.name) if errors else None,
        "report_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(report_path, "w", encoding="utf-8") as repf:
        json.dump(summary, repf, ensure_ascii=False, indent=2)
    print(f"\n✅ all_nodes.jsonl import finished. Inserted: {inserted}, Errors: {len(errors)}")
    if errors:
        print(f"Log: {log_path}")
    print(f"Report: {report_path}")
    with open(json_path, encoding="utf-8") as f:
        try:
            nodes = json.load(f)
        except Exception as e:
            print(f"❌ JSON parse error: {e}")
            return
    if not isinstance(nodes, list):
        print("❌ all_nodes.jsonl must be a list of nodes!")
        return
    total = len(nodes)
    valid_count = [0]
    duplicates = []
    log_path = LOG_DIR / "duplicate_all_nodes.log"
    report_path = LOG_DIR / "import_report_all_nodes.json"
    # فرض: ستون raw در جدول یونیک است
    from tqdm import tqdm
    with tqdm(total=total, desc="all_nodes", ncols=80, leave=True, dynamic_ncols=True, colour='green') as pbar:
        for idx, node in enumerate(nodes, 1):
            try:
                batch_insert("all_nodes", [node], cur, conn, set(), duplicates, valid_count)
            except Exception as e:
                duplicates.append({"raw": node.get("raw"), "reason": str(e)})
            pbar.set_postfix(valid=valid_count[0], dup=len(duplicates))
            pbar.update(1)
    # Write duplicates log
    if duplicates:
        with open(log_path, "w", encoding="utf-8") as dupf:
            for dup in duplicates:
                dupf.write(json.dumps(dup, ensure_ascii=False) + "\n")
    # Write summary report
    summary = {
        "total": total,
        "inserted": valid_count[0],
        "duplicate": len(duplicates),
        "log": str(log_path.name),
        "report_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(report_path, "w", encoding="utf-8") as repf:
        json.dump(summary, repf, ensure_ascii=False, indent=2)
    print(f"\n✅ all_nodes import finished. Inserted: {valid_count[0]}, Duplicate: {len(duplicates)}")
    print(f"Log: {log_path}")
    print(f"Report: {report_path}")
    cur.close()
    conn.close()
    print("\n📊 DB import finished. Check logs/ for duplicates.")

if __name__ == "__main__":
    # برای ایمپورت موازی all_nodes.jsonl:
    jsonl_path = Path(__file__).resolve().parent.parent / "data/tmp/all_nodes.jsonl"
    if jsonl_path.exists():
        import_hysteria_jsonl_parallel(jsonl_path, DB_URL, batch_size=1000, max_workers=4)
    else:
        main()
