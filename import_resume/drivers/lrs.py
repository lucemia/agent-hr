"""
LRS (Google Sheets) resume importer implementation.
"""

from io import StringIO
from typing import Any

import pandas as pd
import requests

from ..interface import ResumeImporter
from ..models import InterviewStatus


class LRSImporter(ResumeImporter):
    """
    Importer for LRS Google Sheets data.

    Handles the specific field mappings and data transformations
    required for the LRS Google Sheets source.
    """

    def __init__(self):
        super().__init__("LRS")
        self.sheet_url = "https://docs.google.com/spreadsheets/d/1mGpl2LzdXZlrKYXatWdAKQrI5SsagjTEen58xtjDNms/export?format=csv&gid=127001815"

    def get_field_mapping(self) -> dict[str, str]:
        """
        Return mapping from LRS Google Sheets field names to Resume model fields.

        The LRS sheet has Chinese column names.
        """
        return {
            "編號": "source_id",
            "名字": "full_name",
            "作答email": "email",
            "履歷": "resume_file",
            "補充說明By LRS": "recruiter_notes",
            "測驗結果": "test_url",
            "筆試分數": "test_score",
            "是否約面": "interview_status",
            "補充說明 By集雅": "hr_notes",
        }

    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """
        Fetch data from LRS Google Sheets.

        Returns:
            DataFrame with raw LRS data

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
            raise ImportError(f"Failed to fetch data from LRS Google Sheets: {e}")

    def apply_source_specific_transforms(
        self, row_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply LRS-specific data transformations.

        Args:
            row_dict: Dictionary of row data

        Returns:
            Transformed row dictionary
        """
        # Convert LRS interview status to our enum
        if "interview_status" in row_dict and row_dict["interview_status"]:
            lrs_status = str(row_dict["interview_status"]).strip()

            if lrs_status in ["是", "約面", "YES", "yes"]:
                row_dict["interview_status"] = InterviewStatus.SCHEDULED
            elif lrs_status in ["否", "NO", "no"]:
                row_dict["interview_status"] = InterviewStatus.NOT_SCHEDULED
            else:
                row_dict["interview_status"] = InterviewStatus.PENDING

        # Convert source_id to string if it exists
        if "source_id" in row_dict and row_dict["source_id"] is not None:
            row_dict["source_id"] = str(row_dict["source_id"])

        # Clean up empty strings to None
        for key, value in row_dict.items():
            if isinstance(value, str) and value.strip() == "":
                row_dict[key] = None

        return row_dict
