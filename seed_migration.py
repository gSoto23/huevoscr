from app.database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    print("Starting migration...")
    with engine.connect() as conn:
        try:
            # Attempt to add delivery_day
            conn.execute(text("ALTER TABLE orders ADD COLUMN delivery_day VARCHAR"))
            print("Added delivery_day column.")
        except Exception as e:
            print(f"Skipping delivery_day (likely exists): {e}")

        try:
            # Attempt to add delivery_date
            conn.execute(text("ALTER TABLE orders ADD COLUMN delivery_date DATETIME"))
            print("Added delivery_date column.")
        except Exception as e:
            print(f"Skipping delivery_date (likely exists): {e}")
            
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
