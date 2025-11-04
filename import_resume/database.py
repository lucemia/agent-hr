"""
Database operations for resume import system.
"""

from typing import List
from pathlib import Path
from sqlmodel import Session, select

from .models import Resume, create_database_engine, create_tables


class ResumeDatabase:
    """Database service for resume operations"""
    
    def __init__(self, db_path: str = "resume.db"):
        self.db_path = db_path
        self.engine = create_database_engine(db_path)
        create_tables(self.engine)
    
    def save_resumes(self, resumes: List[Resume]) -> int:
        """
        Save resume records to database.
        
        Args:
            resumes: List of Resume objects to save
            
        Returns:
            Number of records saved
        """
        with Session(self.engine) as session:
            for resume in resumes:
                session.add(resume)
            session.commit()
        
        return len(resumes)
    
    def get_resumes(self, limit: int = None, source: str = None) -> List[Resume]:
        """
        Retrieve resume records from database.
        
        Args:
            limit: Maximum number of records to return
            source: Filter by source (optional)
            
        Returns:
            List of Resume objects
        """
        with Session(self.engine) as session:
            statement = select(Resume)
            
            if source:
                statement = statement.where(Resume.source == source)
            
            if limit:
                statement = statement.limit(limit)
            
            resumes = session.exec(statement).all()
            return list(resumes)
    
    def count_resumes(self, source: str = None) -> int:
        """
        Count resume records in database.
        
        Args:
            source: Filter by source (optional)
            
        Returns:
            Number of records
        """
        with Session(self.engine) as session:
            statement = select(Resume)
            
            if source:
                statement = statement.where(Resume.source == source)
            
            resumes = session.exec(statement).all()
            return len(resumes)
    
    def database_exists(self) -> bool:
        """Check if database file exists"""
        return Path(self.db_path).exists()