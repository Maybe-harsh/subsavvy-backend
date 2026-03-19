import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base

# Load hidden variables from .env if running locally
load_dotenv()

# FIX: Local DB URL now loaded from .env as LOCAL_DB_URL fallback
# Add this to your backend/.env file:
#   LOCAL_DB_URL=postgresql://postgres:admin@localhost:5432/subscription_tracker
LOCAL_DB_URL = os.getenv("LOCAL_DB_URL", "postgresql://postgres:admin@localhost:5432/subscription_tracker")
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