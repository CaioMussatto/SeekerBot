import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from the .env file
load_dotenv()

# Retrieve database credentials from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# Ensure all critical variables are present
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
    print("❌ ERROR: Missing database configuration in .env file.")
    sys.exit(1)

# Construct the PostgreSQL connection URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create the SQLAlchemy engine responsible for database connections
# echo=False prevents SQLAlchemy from printing every raw SQL query to the terminal
engine = create_engine(DATABASE_URL, echo=False)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our declarative models (tables)
Base = declarative_base()

def get_db():
    """
    Dependency function to yield a database session and ensure it is closed properly.
    This will be used later by the web framework (e.g., FastAPI or Flask) and scripts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()