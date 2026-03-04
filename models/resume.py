import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from core.database import Base
from datetime import datetime, timezone
class Resume(Base):
    """
    SQLAlchemy model representing the 'resumes' table.
    Stores different versions of the user's resume (e.g., LinkedIn, Gupy) 
    and the AI-generated Master CV.
    """
    __tablename__ = 'resumes'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False) # e.g., "LinkedIn CV", "Master AI CV"
    content = Column(Text, nullable=False)      # The extracted text from the PDF
    
    # Flag to easily identify which resume is the main one used for AI matching
    is_master = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, 
                   default=datetime.now(timezone.utc), 
                   onupdate=lambda: datetime.now(timezone.utc))