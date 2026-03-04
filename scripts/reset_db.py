from core.database import engine, Base
from sqlalchemy import MetaData

# Import ALL your models here so SQLAlchemy knows what to recreate
from models.job import Job
from models.resume import Resume

# If you have a match model, we try to import it so it gets recreated too
try:
    from models.match import Match
except ImportError:
    pass

def reset_database():
    """
    Reflects the current database state to correctly handle Foreign Key dependencies,
    drops all tables in the correct order, and recreates them with the new schema.
    """
    print("🗑️  Analyzing database dependencies and dropping tables...")
    
    # Create a temporary MetaData instance to reflect the current DB state
    meta = MetaData()
    meta.reflect(bind=engine)
    
    # Drop all tables found in the database (handles FK order automatically)
    meta.drop_all(bind=engine)
    
    print("🏗️  Creating tables with the updated schema...")
    # Base.metadata contains the NEW schema defined in your Python classes
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database reset successfully! New schema applied.")

if __name__ == "__main__":
    reset_database()