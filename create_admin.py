from app.database import SessionLocal, engine, Base
from app.models import User
from app.auth import get_password_hash
import sys

def create_admin_user(username, password):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if user exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"User {username} already exists.")
        db.close()
        return

    hashed_pw = get_password_hash(password)
    new_user = User(username=username, password_hash=hashed_pw, role="admin")
    db.add(new_user)
    db.commit()
    print(f"Admin user '{username}' created successfully.")
    db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password>")
    else:
        create_admin_user(sys.argv[1], sys.argv[2])
