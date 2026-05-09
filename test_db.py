import psycopg2

DATABASE_URL = "postgresql://admin:nbnCtpSrUGDjrzj8ri8Ac4z46oP9i3wS@dpg-d7oqgrgg4nts7384egu0-a.oregon-postgres.render.com/price_db_497f"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM products;")
print("Total products:", cur.fetchone()[0])

conn.close()