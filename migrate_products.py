import sqlite3
import psycopg2
from psycopg2.extras import execute_batch

# --- SQLite (your local DB) ---
sqlite_conn = sqlite3.connect("instance/market.db")
sqlite_cursor = sqlite_conn.cursor()

# --- PostgreSQL (Render) ---
DATABASE_URL = "postgresql://admin:nbnCtpSrUGDjrzj8ri8Ac4z46oP9i3wS@dpg-d7oqgrgg4nts7384egu0-a.oregon-postgres.render.com/price_db_497f"
pg_conn = psycopg2.connect(DATABASE_URL)
pg_cursor = pg_conn.cursor()

# Fetch data from SQLite
sqlite_cursor.execute("SELECT product_name, price FROM products")
rows = sqlite_cursor.fetchall()

print(f"📦 Found {len(rows)} products")

# Insert into PostgreSQL (fast batch)
execute_batch(
    pg_cursor,
    "INSERT INTO products (product_name, price) VALUES (%s, %s)",
    rows
)

pg_conn.commit()

print("✅ Products migrated successfully!")

# Close connections
sqlite_conn.close()
pg_conn.close()