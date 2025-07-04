import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from logs.log import LoggerManager

class DatabaseManager:
    @staticmethod
    def check_env():
        ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
        if not ENV_PATH.exists():
            print(f"⚠️  .env file not found at {ENV_PATH}")
            return False
        load_dotenv(dotenv_path=ENV_PATH)
        db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or os.getenv("POSTGRES_URL")
        if not db_url:
            print("❌ No database URL found in .env. Please set DATABASE_URL, DB_URL, or POSTGRES_URL.")
            return False
        return True

    def __init__(self):
        ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
        if ENV_PATH.exists():
            load_dotenv(dotenv_path=ENV_PATH)
        self.db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or os.getenv("POSTGRES_URL")
        if not self.db_url:
            LoggerManager.get_logger("DatabaseManager").error("No database URL found in .env. Please set DATABASE_URL, DB_URL, or POSTGRES_URL.")
            raise Exception("No database URL found in .env")
        self.logger = LoggerManager.get_logger("DatabaseManager")

    def __enter__(self):
        self.conn = psycopg2.connect(self.db_url)
        self.cur = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cur.close()
        self.conn.close()

    def insert(self, table, data_dict):
        columns = ', '.join(f'"{k}"' for k in data_dict.keys())
        placeholders = ', '.join(['%s'] * len(data_dict))
        values = list(data_dict.values())
        query = f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders}) RETURNING id'
        self.cur.execute(query, values)
        inserted_id = self.cur.fetchone()[0]
        self.conn.commit()
        self.logger.info(f"Inserted row into {table} with id {inserted_id}")
        return inserted_id

    def insert_batch(self, table, data_list):
        if not data_list:
            return []
        columns = ', '.join(f'"{k}"' for k in data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(data_list[0]))
        query = f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders}) RETURNING id'
        ids = []
        for data in data_list:
            self.cur.execute(query, list(data.values()))
            ids.append(self.cur.fetchone()[0])
        self.conn.commit()
        self.logger.info(f"Batch inserted {len(ids)} rows into {table}")
        return ids

    def get(self, table, limit=10, order_by="created_at", desc=True):
        order = "DESC" if desc else "ASC"
        query = f'SELECT * FROM "{table}" ORDER BY {order_by} {order} LIMIT %s'
        self.cur.execute(query, (limit,))
        rows = self.cur.fetchall()
        colnames = [desc[0] for desc in self.cur.description]
        return [dict(zip(colnames, row)) for row in rows]

    def get_by_id(self, table, row_id):
        query = f'SELECT * FROM "{table}" WHERE id = %s'
        self.cur.execute(query, (row_id,))
        row = self.cur.fetchone()
        if row:
            colnames = [desc[0] for desc in self.cur.description]
            return dict(zip(colnames, row))
        return None

    def get_column(self, table, column, limit=10, order_by="created_at", desc=True):
        order = "DESC" if desc else "ASC"
        query = f'SELECT {column} FROM "{table}" ORDER BY {order_by} {order} LIMIT %s'
        self.cur.execute(query, (limit,))
        return [row[0] for row in self.cur.fetchall()]

    def get_by_filter(self, table, filters: dict, limit=10, order_by="created_at", desc=True):
        order = "DESC" if desc else "ASC"
        where = ' AND '.join([f'{k} = %s' for k in filters.keys()])
        query = f'SELECT * FROM "{table}" WHERE {where} ORDER BY {order_by} {order} LIMIT %s'
        values = list(filters.values()) + [limit]
        self.cur.execute(query, values)
        rows = self.cur.fetchall()
        colnames = [desc[0] for desc in self.cur.description]
        return [dict(zip(colnames, row)) for row in rows]

    def get_cell(self, table, column, row_id):
        query = f'SELECT {column} FROM "{table}" WHERE id = %s'
        self.cur.execute(query, (row_id,))
        row = self.cur.fetchone()
        return row[0] if row else None

# # Example usage:
# from config.database import DatabaseManager
# with DatabaseManager() as db:
#     db.insert(...)
#     db.get(...)
#     db.get_by_filter(...)
#     db.insert_batch(...)
