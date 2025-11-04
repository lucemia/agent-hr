"""
Yourator (Excel file) resume importer implementation.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ..interface import ResumeImporter
from ..models import ApplicationStatus


class YouratorImporter(ResumeImporter):
    """
    Importer for Yourator Excel file data.

    Handles the specific field mappings and data transformations
    required for the Yourator Excel file source.
    """

    def __init__(self):
        super().__init__("Yourator")
        self.file_path = "./yourator.xlsx"

    def get_field_mapping(self) -> dict[str, str]:
        """
        Return mapping from Yourator Excel field names to Resume model fields.

        The Yourator file has Chinese column names.
        """
        return {
            "投遞編號": "source_id",
            "求職者姓名": "full_name",
            "求職者信箱": "email",
            "求職者電話": "phone",
            "職位名稱": "position_applied",
            "投遞時間": "application_date",
            "投遞狀態": "application_status",
            "履歷連結": "resume_file",
            "簡介": "recruiter_notes",
            "學歷一": "technical_notes",  # Using technical_notes for education info
            "工作經歷一": "hr_notes",  # Using hr_notes for work experience
        }

    def fetch_data(self, file_path: str = None, **kwargs) -> pd.DataFrame:
        """
        Fetch data from Yourator Excel file.

        Args:
            file_path: Optional path to Excel file, defaults to ./yourator.xlsx

        Returns:
            DataFrame with raw Yourator data

        Raises:
            ImportError: If file cannot be read
        """
        try:
            excel_file = Path(file_path or self.file_path)
            if not excel_file.exists():
                raise ImportError(f"Excel file not found: {excel_file}")

            # Read Excel file
            df = pd.read_excel(excel_file)
            return df

        except Exception as e:
            raise ImportError(f"Failed to read Yourator Excel file: {e}")

    def apply_source_specific_transforms(
        self, row_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply Yourator-specific data transformations.

        Args:
            row_dict: Dictionary of row data

        Returns:
            Transformed row dictionary
        """
        # Convert application date string to datetime
        if "application_date" in row_dict and row_dict["application_date"]:
            try:
                if isinstance(row_dict["application_date"], str):
                    # Parse datetime string like "2025-05-05 16:38:29"
                    row_dict["application_date"] = datetime.strptime(
                        row_dict["application_date"], "%Y-%m-%d %H:%M:%S"
                    )
            except (ValueError, TypeError):
                row_dict["application_date"] = None

        # Convert Yourator application status to our enum
        if "application_status" in row_dict and row_dict["application_status"]:
            status_str = str(row_dict["application_status"]).strip()

            if status_str in ["待審核", "pending", "submitted"]:
                row_dict["application_status"] = ApplicationStatus.APPLIED
            elif status_str in ["審核中", "reviewing", "screening"]:
                row_dict["application_status"] = ApplicationStatus.SCREENING
            elif status_str in ["面試", "interview", "interviewing"]:
                row_dict["application_status"] = ApplicationStatus.INTERVIEW
            elif status_str in ["錄取", "hired", "accepted"]:
                row_dict["application_status"] = ApplicationStatus.HIRED
            elif status_str in ["拒絕", "rejected", "declined"]:
                row_dict["application_status"] = ApplicationStatus.REJECTED
            else:
                row_dict["application_status"] = ApplicationStatus.APPLIED  # Default

        # Convert source_id to string if it exists
        if "source_id" in row_dict and row_dict["source_id"] is not None:
            row_dict["source_id"] = str(row_dict["source_id"])

        # Clean up phone number format
        if "phone" in row_dict and row_dict["phone"]:
            phone = str(row_dict["phone"]).strip()
            # Remove common phone formatting
            phone = (
                phone.replace("(", "")
                .replace(")", "")
                .replace("-", "")
                .replace(" ", "")
            )
            row_dict["phone"] = phone if phone else None

        # Clean up empty strings and NaN values to None
        for key, value in row_dict.items():
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ""):
                row_dict[key] = None

        return row_dict
