import sqlite3

# Connect to the database
conn = sqlite3.connect('huevoscr.db')
cursor = conn.cursor()

# Add columns to customers table
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN pending_receipt_media_id VARCHAR")
    print("Added pending_receipt_media_id column")
except sqlite3.OperationalError as e:
    print(f"pending_receipt_media_id likely exists: {e}")

try:
    cursor.execute("ALTER TABLE customers ADD COLUMN pending_receipt_caption TEXT")
    print("Added pending_receipt_caption column")
except sqlite3.OperationalError as e:
    print(f"pending_receipt_caption likely exists: {e}")

try:
    cursor.execute("ALTER TABLE customers ADD COLUMN pending_receipt_ts DATETIME")
    print("Added pending_receipt_ts column")
except sqlite3.OperationalError as e:
    print(f"pending_receipt_ts likely exists: {e}")

try:
    cursor.execute("ALTER TABLE customers ADD COLUMN pending_receipt_for_order_id INTEGER")
    print("Added pending_receipt_for_order_id column")
except sqlite3.OperationalError as e:
    print(f"pending_receipt_for_order_id likely exists: {e}")

conn.commit()
conn.close()
print("Migration completed.")
