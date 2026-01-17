from app.database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    print("Starting migration 2 (Customer Context)...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE customers ADD COLUMN last_message_content TEXT"))
            print("Added last_message_content column.")
        except Exception as e:
            print(f"Skipping last_message_content (likely exists): {e}")

        try:
            conn.execute(text("ALTER TABLE customers ADD COLUMN last_message_ts DATETIME"))
            print("Added last_message_ts column.")
        except Exception as e:
            print(f"Skipping last_message_ts (likely exists): {e}")
            
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
