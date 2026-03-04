import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
# Import the declarative Base from our core database configuration
from core.database import Base
from datetime import datetime, timezone


class Job(Base):
    """
    SQLAlchemy model representing the 'jobs' table in the PostgreSQL database.
    Stores all scraped job postings and their metadata.
    """
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255))
    location = Column(String(255))
    link = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    source = Column(String(100))
    
    # Status tracking
    applied = Column(Boolean, default=False)
    
    # ESSENTIAL: Prevents deleted/rejected jobs from reappearing in future scrapes
    rejected = Column(Boolean, default=False) 
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    published_at = Column(String(50))
    match_score = Column(Integer, nullable=True)
    match_rationale = Column(Text, nullable=True)