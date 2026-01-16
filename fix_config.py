from app.database import SessionLocal
from app.models import Config

db = SessionLocal()

# The UI uses 'price_carton'. I introduced 'carton_price' by mistake in the seed.
# I will remove 'carton_price' so we only have one source of truth.

duplicate = db.query(Config).filter(Config.key == "carton_price").first()
if duplicate:
    print(f"Deleting duplicate key: {duplicate.key} (Value: {duplicate.value})")
    db.delete(duplicate)
    db.commit()
else:
    print("No duplicate found.")

# Verify what remains
remaining = db.query(Config).all()
print("\nCurrent Configs:")
for c in remaining:
    print(f"{c.key}: {c.value}")

db.close()
