import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('huevoscr.db')
        cursor = conn.cursor()
        
        # Add columns
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN has_attachment BOOLEAN DEFAULT 0")
            print("Added has_attachment")
        except sqlite3.OperationalError as e:
            print(f"Skipping has_attachment: {e}")

        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN receipt_media_id VARCHAR")
            print("Added receipt_media_id")
        except sqlite3.OperationalError as e:
            print(f"Skipping receipt_media_id: {e}")

        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN receipt_caption TEXT")
            print("Added receipt_caption")
        except sqlite3.OperationalError as e:
            print(f"Skipping receipt_caption: {e}")
            
        conn.commit()
        conn.close()
        print("Migration complete")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
