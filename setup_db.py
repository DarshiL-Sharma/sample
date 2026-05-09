import psycopg2

DATABASE_URL = "postgresql://admin:nbnCtpSrUGDjrzj8ri8Ac4z46oP9i3wS@dpg-d7oqgrgg4nts7384egu0-a.oregon-postgres.render.com/price_db_497f"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Transactions table (your scanned bill data)
cur.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    product_name TEXT,
    vendor TEXT,
    amount REAL,
    subtotal REAL,
    total REAL,
    date TEXT,
    invoice_no TEXT
);
""")

# Products table (30k items)
cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_name TEXT,
    price REAL
);
""")

conn.commit()
conn.close()

print("✅ Tables created successfully!")