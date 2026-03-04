import sys
# Import the engine and Base from our core configuration
from core.database import engine, Base

# IMPORTANT: We must import all models here before calling create_all()
# so SQLAlchemy knows they exist and can map them to tables.
from models.job import Job
from models.job import Job
from models.resume import Resume
from models.match import Match

def initialize_database(reset: bool = False):
    """
    Creates all tables defined in the SQLAlchemy models.
    
    Args:
        reset (bool): If True, drops all existing tables before creating them.
                      WARNING: This deletes all data.
    """
    try:
        if reset:
            print("🗑️ Resetting database (Dropping all tables)...")
            Base.metadata.drop_all(bind=engine)
            
        print("🔨 Creating tables...")
        # create_all only creates tables that do not exist yet
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database initialized successfully with all tables!")
        
    except Exception as e:
        print(f"❌ Error initializing the database: {e}")

if __name__ == "__main__":
    # Allows running `uv run python init_db.py --reset` from the terminal
    should_reset = "--reset" in sys.argv
    initialize_database(reset=should_reset)