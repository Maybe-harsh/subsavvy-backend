import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base # Importing the Base we created in models.py

# Load hidden variables from .env if running locally
load_dotenv()

# Grab the database URL from Render's Environment Variables.
# If it's not found (like on your local laptop), it falls back to your local pgAdmin database!
LOCAL_DB_URL = "postgresql://postgres:admin@localhost:5432/subscription_tracker"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", LOCAL_DB_URL)

# FIX: Render gives 'postgres://' URLs, but SQLAlchemy strictly requires 'postgresql://'
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

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