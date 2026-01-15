from app.database import SessionLocal, engine
from app import models, auth

def seed():
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if admin exists
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        print("Creating admin user...")
        hashed_pw = auth.get_password_hash("admin")
        admin_user = models.User(username="admin", password_hash=hashed_pw, role="admin", is_active=True)
        db.add(admin_user)
    
    # Check if seller exists
    seller = db.query(models.User).filter(models.User.username == "vendedor1").first()
    if not seller:
        print("Creating seller user...")
        hashed_pw = auth.get_password_hash("1234")
        seller_user = models.User(username="vendedor1", password_hash=hashed_pw, role="seller", is_active=True)
        db.add(seller_user)

    db.commit()

    # Get seller id
    seller = db.query(models.User).filter(models.User.username == "vendedor1").first()
    
    # Create Test Customer
    cust = db.query(models.Customer).filter(models.Customer.whatsapp_id == "88888888").first()
    if not cust:
        print("Creating test customer...")
        cust_user = models.Customer(
            whatsapp_id="88888888",
            name="Cliente Prueba",
            address="San Jose Centro, 100m norte del parque",
            cartons_qty=2,
            periodicity="Semanal",
            payment_method="Sinpe",
            is_active=True,
            seller_id=seller.id
        )
        db.add(cust_user)
    
    db.commit()
    db.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed()
