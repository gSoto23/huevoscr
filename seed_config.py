from app.database import SessionLocal
from app.models import Config

db = SessionLocal()

defaults = {
    "delivery_days": "Lunes y Jueves",
    "carton_price": "3500",
    "currency_symbol": "₡"
}

for key, value in defaults.items():
    existing = db.query(Config).filter(Config.key == key).first()
    if not existing:
        print(f"Creating {key} = {value}")
        config = Config(key=key, value=value)
        db.add(config)
    else:
        print(f"Skipping {key} (already exists)")

db.commit()
db.close()
