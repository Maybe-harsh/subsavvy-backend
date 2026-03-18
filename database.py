from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base # Importing the Base we created in models.py

# Replace this with your actual PostgreSQL credentials later
# Format: postgresql://user:password@localhost:5432/dbname
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:admin@localhost:5432/subscription_tracker"

# The engine is responsible for establishing the core connection
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# SessionLocal is what we use to create individual database sessions for each request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to inject the database session into your FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()