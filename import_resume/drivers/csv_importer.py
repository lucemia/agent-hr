"""
CSV file resume importer implementation.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from ..interface import ResumeImporter


class CSVImporter(ResumeImporter):
    """
    Importer for standard CSV files.

    Handles CSV files with common field names.
    """

    def __init__(self):
        super().__init__("CSV")

    def get_field_mapping(self) -> dict[str, str]:
        """
        Return mapping from standard CSV field names to Resume model fields.
        """
        return {
            "id": "source_id",
            "name": "full_name",
            "full_name": "full_name",
            "email": "email",
            "phone": "phone",
            "resume": "resume_file",
            "resume_file": "resume_file",
            "position": "position_applied",
            "position_applied": "position_applied",
            "test_score": "test_score",
            "test_url": "test_url",
            "interview_status": "interview_status",
            "application_status": "application_status",
            "recruiter_notes": "recruiter_notes",
            "hr_notes": "hr_notes",
            "technical_notes": "technical_notes",
            "skills": "skills",
            "experience": "years_experience",
            "years_experience": "years_experience",
        }

    def fetch_data(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        Fetch data from CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            DataFrame with CSV data

        Raises:
            ImportError: If file cannot be read
        """
        try:
            csv_file = Path(file_path)
            if not csv_file.exists():
                raise ImportError(f"CSV file not found: {csv_file}")

            df = pd.read_csv(csv_file)
            return df

        except Exception as e:
            raise ImportError(f"Failed to read CSV file: {e}")

    def apply_source_specific_transforms(
        self, row_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply CSV-specific data transformations.

        Args:
            row_dict: Dictionary of row data

        Returns:
            Transformed row dictionary
        """
        # Convert source_id to string if it exists
        if "source_id" in row_dict and row_dict["source_id"] is not None:
            row_dict["source_id"] = str(row_dict["source_id"])

        # Clean up empty strings to None
        for key, value in row_dict.items():
            if isinstance(value, str) and value.strip() == "":
                row_dict[key] = None

        return row_dict
