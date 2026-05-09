import sqlite3
import psycopg2
from psycopg2.extras import execute_batch

try:
    # --- SQLite (your bills.db) ---
    sqlite_conn = sqlite3.connect("instance/bills.db")
    sqlite_cursor = sqlite_conn.cursor()

    # ✅ Correct table name from your DB
    TABLE_NAME = "Product_data"

    # --- PostgreSQL ---
    DATABASE_URL = "postgresql://admin:nbnCtpSrUGDjrzj8ri8Ac4z46oP9i3wS@dpg-d7oqgrgg4nts7384egu0-a.oregon-postgres.render.com/price_db_497f"
    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cursor = pg_conn.cursor()

    # Fetch data from SQLite
    sqlite_cursor.execute(f"""
    SELECT product_name, vendor, amount, subtotal, total, date, invoice_no 
    FROM {TABLE_NAME}
    """)

    rows = sqlite_cursor.fetchall()

    print(f"📦 Found {len(rows)} transaction records")

    # Clean bad rows (important for OCR data)
    clean_rows = []
    for row in rows:
        product_name, vendor, amount, subtotal, total, date, invoice_no = row

        # Skip completely empty product
        if not product_name:
            continue


        # Fix numeric fields
        def to_float(value):
            try:
                if value == "" or value is None:
                    return None
                return float(value)
            except:
                return None


        amount = to_float(amount)
        subtotal = to_float(subtotal)
        total = to_float(total)

        # Fix text fields
        vendor = vendor if vendor != "" else None
        date = date if date != "" else None
        invoice_no = invoice_no if invoice_no != "" else None

        clean_rows.append((
            product_name,
            vendor,
            amount,
            subtotal,
            total,
            date,
            invoice_no
        ))

    print(f"🧹 Cleaned rows: {len(clean_rows)}")

    # Insert into PostgreSQL
    execute_batch(
        pg_cursor,
        """
        INSERT INTO transactions 
        (product_name, vendor, amount, subtotal, total, date, invoice_no)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        clean_rows
    )

    pg_conn.commit()

    print("✅ Transactions migrated successfully!")

except Exception as e:
    print("❌ ERROR:", e)

finally:
    try:
        sqlite_conn.close()
        pg_conn.close()
    except:
        pass