"""
Cake (Google Sheets) resume importer implementation.
"""

from io import StringIO
from typing import Any

import pandas as pd
import requests

from ..interface import ResumeImporter
from ..models import InterviewStatus


class CakeImporter(ResumeImporter):
    """
    Importer for Cake Google Sheets data.

    Handles the specific field mappings and data transformations
    required for the Cake Google Sheets source.
    """

    def __init__(self):
        super().__init__("Cake")
        self.sheet_url = "https://docs.google.com/spreadsheets/d/1hinp7M0dyMdL6bnoq4hRv4iHuwa9CuZzd8Xs8pdwoOo/export?format=csv&gid=341040725"

    def get_field_mapping(self) -> dict[str, str]:
        """
        Return mapping from Cake Google Sheets field names to Resume model fields.

        The Cake sheet has mixed Chinese/English column names.
        """
        return {
            "名字": "full_name",
            "email": "email",
            "分數": "test_score",
            "測驗結果": "test_url",
            "履歷": "resume_file",
            "是否約面": "interview_status",
            "是否約面.1": "interview_status_2",  # backup field
            "職缺": "position_applied",
            "補充說明": "recruiter_notes",
            "Comment": "hr_notes",
            "FROM": "source_id",
        }

    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """
        Fetch data from Cake Google Sheets.

        Returns:
            DataFrame with raw Cake data

        Raises:
            requests.RequestException: If data cannot be fetched
        """
        try:
            response = requests.get(self.sheet_url)
            response.raise_for_status()

            # Ensure proper UTF-8 encoding
            response.encoding = "utf-8"

            # Read CSV data into pandas DataFrame with UTF-8 encoding
            df = pd.read_csv(StringIO(response.text), encoding="utf-8")
            return df

        except requests.RequestException as e:
            raise ImportError(f"Failed to fetch data from Cake Google Sheets: {e}")

    def apply_source_specific_transforms(
        self, row_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply Cake-specific data transformations.

        Args:
            row_dict: Dictionary of row data

        Returns:
            Transformed row dictionary
        """
        # Handle test score - convert percentage string to float
        if "test_score" in row_dict and row_dict["test_score"]:
            score_str = str(row_dict["test_score"]).strip()
            if score_str.endswith("%"):
                try:
                    # Remove % and convert to float
                    score_value = float(score_str[:-1])
                    row_dict["test_score"] = score_value
                except ValueError:
                    row_dict["test_score"] = None
            else:
                try:
                    row_dict["test_score"] = float(score_str)
                except ValueError:
                    row_dict["test_score"] = None

        # Convert Cake interview status to our enum
        # Check both interview status fields
        interview_status = None
        if "interview_status" in row_dict and row_dict["interview_status"] is not None:
            interview_status = row_dict["interview_status"]
        elif (
            "interview_status_2" in row_dict
            and row_dict["interview_status_2"] is not None
        ):
            interview_status = row_dict["interview_status_2"]

        if interview_status is not None:
            if isinstance(interview_status, bool):
                if interview_status:
                    row_dict["interview_status"] = InterviewStatus.SCHEDULED
                else:
                    row_dict["interview_status"] = InterviewStatus.NOT_SCHEDULED
            elif isinstance(interview_status, str):
                status_str = interview_status.strip().lower()
                if status_str in ["true", "yes", "是", "約面"]:
                    row_dict["interview_status"] = InterviewStatus.SCHEDULED
                elif status_str in ["false", "no", "否"]:
                    row_dict["interview_status"] = InterviewStatus.NOT_SCHEDULED
                else:
                    row_dict["interview_status"] = InterviewStatus.PENDING
            else:
                row_dict["interview_status"] = InterviewStatus.PENDING

        # Remove the backup interview status field
        if "interview_status_2" in row_dict:
            del row_dict["interview_status_2"]

        # Convert source_id to string if it exists
        if "source_id" in row_dict and row_dict["source_id"] is not None:
            row_dict["source_id"] = str(row_dict["source_id"])

        # Clean up empty strings to None
        for key, value in row_dict.items():
            if isinstance(value, str) and value.strip() == "":
                row_dict[key] = None

        return row_dict
