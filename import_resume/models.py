"""
Data models for resume import system.
"""

import re
from datetime import datetime
from enum import Enum

from pydantic import validator
from sqlmodel import Field, SQLModel, create_engine


class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    HIRED = "hired"
    WITHDRAWN = "withdrawn"


class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    NOT_SCHEDULED = "not_scheduled"


class Resume(SQLModel, table=True):
    """
    Common resume model that can handle data from various sources.
    Uses standard field names that are common across different resume sources.
    """

    # Primary key
    id: int | None = Field(default=None, primary_key=True)

    # Core candidate information
    full_name: str | None = Field(
        default=None, description="Full name of the candidate"
    )
    email: str | None = Field(default=None, description="Email address")
    phone: str | None = Field(default=None, description="Phone number")

    # Resume/Application details
    resume_file: str | None = Field(
        default=None, description="Path or name of resume file"
    )
    position_applied: str | None = Field(
        default=None, description="Position applied for"
    )
    application_date: datetime | None = Field(
        default=None, description="Date of application"
    )

    # Assessment information
    test_score: float | None = Field(
        default=None, description="Test or assessment score"
    )
    test_url: str | None = Field(default=None, description="URL to test results")

    # Interview information
    interview_status: InterviewStatus | None = Field(
        default=None, description="Interview status"
    )
    interview_date: datetime | None = Field(default=None, description="Interview date")

    # Application status
    application_status: ApplicationStatus | None = Field(
        default=None, description="Current application status"
    )

    # Notes and comments
    recruiter_notes: str | None = Field(
        default=None, description="Notes from recruiter"
    )
    hr_notes: str | None = Field(default=None, description="Notes from HR")
    technical_notes: str | None = Field(
        default=None, description="Technical assessment notes"
    )

    # Experience and skills
    years_experience: int | None = Field(
        default=None, description="Years of experience"
    )
    skills: str | None = Field(default=None, description="Skills (comma-separated)")

    # Source tracking
    source: str | None = Field(
        default=None, description="Source of the resume (lrs, linkedin, hr, etc.)"
    )
    source_id: str | None = Field(default=None, description="ID from the source system")

    # Metadata
    created_at: datetime | None = Field(
        default_factory=datetime.utcnow, description="Record creation time"
    )
    updated_at: datetime | None = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )

    @validator("email")
    def validate_email(cls, v):
        if v is None or v == "":
            return None
        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError(f"Invalid email format: {v}")
        return v.lower().strip()

    @validator("full_name")
    def validate_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v.strip() if v else None

    @validator("test_score")
    def validate_test_score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Test score must be between 0 and 100")
        return v

    @validator("years_experience")
    def validate_years_experience(cls, v):
        if v is not None and v < 0:
            raise ValueError("Years of experience cannot be negative")
        return v

    def is_complete(self) -> bool:
        """Check if resume has minimum required fields"""
        return self.full_name is not None and self.email is not None


class ResumeValidationError(SQLModel):
    """Model for validation errors"""

    row_index: int
    field: str
    error: str
    raw_value: str


def create_database_engine(db_path: str = "resume.db"):
    """Create SQLite database engine"""
    sqlite_url = f"sqlite:///{db_path}"
    engine = create_engine(sqlite_url, echo=False)
    return engine


def create_tables(engine):
    """Create all tables in the database"""
    SQLModel.metadata.create_all(engine)
