
import sys
import os
from datetime import timedelta

# Add parent directory to path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import auth
from app.database import SessionLocal, engine
from app import models

def create_long_lived_token(username):
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.username == username).first()
    db.close()

    if not user:
        print(f"User {username} not found!")
        return

    # 10 Years
    expires = timedelta(days=365*10)
    
    token = auth.create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=expires
    )
    
    print(f"\n--- LONG LIVED TOKEN FOR {username} (10 YEARS) ---\n")
    print(token)
    print("\n-------------------------------------------------\n")

if __name__ == "__main__":
    create_long_lived_token("admin")
