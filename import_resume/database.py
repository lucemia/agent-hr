"""
Database operations for resume import system.
"""

import shutil
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from .models import Resume, create_database_engine, create_tables


class ResumeDatabase:
    """Database service for resume operations"""

    def __init__(self, db_path: str = "resume.db", backup_dir: str = "backup/resume_files"):
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.engine = create_database_engine(db_path)
        create_tables(self.engine)
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _backup_resume_file(self, resume_file: str | None, source: str | None = None) -> None:
        """
        Backup a resume file to the backup folder.

        Args:
            resume_file: Path or name of the resume file
            source: Source of the resume (for organizing backups)
        """
        if not resume_file:
            return

        # Skip if it's a URL
        if resume_file.startswith(("http://", "https://")):
            return

        # Try to resolve the file path
        file_path = Path(resume_file)
        
        # If it's not an absolute path, try relative to current working directory
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            return

        # Create backup filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = file_path.stem
        file_suffix = file_path.suffix
        
        # Create unique backup filename
        backup_filename = f"{timestamp}_{file_stem}{file_suffix}"
        
        # If source is provided, organize by source
        if source:
            source_backup_dir = self.backup_dir / source
            source_backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = source_backup_dir / backup_filename
        else:
            backup_path = self.backup_dir / backup_filename

        # Copy file to backup location
        try:
            shutil.copy2(file_path, backup_path)
        except Exception:
            # Silently fail if backup fails (don't stop the import process)
            pass

    def _find_existing_resume(
        self, session: Session, resume: Resume
    ) -> Resume | None:
        """
        Find an existing resume record that matches the given resume.
        
        Uses source + email as the unique key to identify duplicates.
        Each person (email) from each source should only have one record.
        
        Args:
            session: Database session
            resume: Resume object to check
            
        Returns:
            Existing Resume object if found, None otherwise
        """
        # Primary check: email + source (unique key)
        if resume.email and resume.source:
            existing = session.exec(
                select(Resume).where(
                    Resume.email == resume.email,
                    Resume.source == resume.source,
                )
            ).first()
            if existing:
                return existing
        
        return None

    def save_resumes(self, resumes: list[Resume]) -> int:
        """
        Save resume records to database with deduplication.
        
        If a resume already exists (based on email + source + position_applied or source_id + source),
        it will be updated instead of creating a duplicate.

        Args:
            resumes: List of Resume objects to save

        Returns:
            Number of records saved (new or updated)
        """
        # Backup resume files before saving
        for resume in resumes:
            if resume.resume_file:
                self._backup_resume_file(resume.resume_file, resume.source)

        new_count = 0
        updated_count = 0

        with Session(self.engine) as session:
            for resume in resumes:
                # Check if record already exists
                existing = self._find_existing_resume(session, resume)
                
                if existing:
                    # Update existing record
                    # Update all fields except id and created_at
                    for field_name in Resume.model_fields.keys():
                        if field_name not in ("id", "created_at"):
                            setattr(existing, field_name, getattr(resume, field_name))
                    
                    # Update updated_at timestamp
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                    updated_count += 1
                else:
                    # New record, add it
                    session.add(resume)
                    new_count += 1
            
            session.commit()

        return new_count + updated_count

    def get_resumes(self, limit: int = None, source: str = None) -> list[Resume]:
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

    def remove_duplicates(self) -> int:
        """
        Remove duplicate records based on email + source.
        Keeps the record with the most recent updated_at timestamp.

        Returns:
            Number of duplicate records removed
        """
        with Session(self.engine) as session:
            # Find all duplicate groups
            statement = select(
                Resume.email,
                Resume.source,
                Resume.id,
                Resume.updated_at,
            ).where(
                Resume.email.isnot(None),
                Resume.source.isnot(None),
            )
            
            resumes = session.exec(statement).all()
            
            # Group by email + source
            groups = {}
            for resume in resumes:
                key = (resume.email, resume.source)
                if key not in groups:
                    groups[key] = []
                groups[key].append((resume.id, resume.updated_at or resume.created_at))
            
            # Find duplicates (groups with more than 1 record)
            duplicates_to_remove = []
            for key, records in groups.items():
                if len(records) > 1:
                    # Sort by updated_at (most recent first)
                    records.sort(key=lambda x: x[1] or datetime.min, reverse=True)
                    # Keep the first one (most recent), mark others for removal
                    for record_id, _ in records[1:]:
                        duplicates_to_remove.append(record_id)
            
            # Remove duplicates
            removed_count = 0
            for record_id in duplicates_to_remove:
                resume = session.get(Resume, record_id)
                if resume:
                    session.delete(resume)
                    removed_count += 1
            
            session.commit()
            return removed_count
