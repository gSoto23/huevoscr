from app.database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    print("Starting n8n_context migration...")
    with engine.connect() as conn:
        try:
            # Attempt to add n8n_context
            conn.execute(text("ALTER TABLE orders ADD COLUMN n8n_context TEXT"))
            print("Added n8n_context column.")
        except Exception as e:
            print(f"Skipping n8n_context (likely exists): {e}")
            
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
