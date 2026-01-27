from app.database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    print("Starting customer n8n_context migration...")
    with engine.connect() as conn:
        try:
            # Attempt to add n8n_context to customers
            conn.execute(text("ALTER TABLE customers ADD COLUMN n8n_context TEXT"))
            print("Added n8n_context column to customers.")
        except Exception as e:
            print(f"Skipping n8n_context (likely exists): {e}")

        # Optional: Drop from orders if desired, but safer to keep for now or ignore
            
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
