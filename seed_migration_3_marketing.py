from app.database import engine, Base
from app import models

# Import models to ensure they are registered with Base.metadata
# They are imported inside `app.models`

if __name__ == "__main__":
    print("Migrating Marketing tables...")
    # This will create any missing tables (like marketing_templates, campaigns, campaign_recipients)
    Base.metadata.create_all(bind=engine)
    print("Marketing tables created successfully.")
