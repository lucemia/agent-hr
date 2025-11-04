"""Tests for LRS importer."""

from unittest.mock import patch

import pandas as pd
import pytest

from import_resume.drivers.lrs import LRSImporter
from import_resume.models import InterviewStatus


class TestLRSImporter:
    """Test cases for LRS importer."""

    def test_init(self):
        """Test LRS importer initialization."""
        importer = LRSImporter()
        assert importer.source_name == "LRS"
        assert "1mGpl2LzdXZlrKYXatWdAKQrI5SsagjTEen58xtjDNms" in importer.sheet_url
        assert "gid=127001815" in importer.sheet_url

    def test_get_field_mapping(self):
        """Test field mapping configuration."""
        importer = LRSImporter()
        mapping = importer.get_field_mapping()

        expected_mappings = {
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

        assert mapping == expected_mappings

    @patch("import_resume.drivers.lrs.requests.get")
    def test_fetch_data_success(
        self, mock_get, sample_lrs_csv_data, mock_requests_response
    ):
        """Test successful data fetching."""
        # Setup mock response
        mock_response = mock_requests_response(sample_lrs_csv_data)
        mock_get.return_value = mock_response

        importer = LRSImporter()
        df = importer.fetch_data()

        # Verify request was made correctly
        mock_get.assert_called_once_with(importer.sheet_url, timeout=30)

        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "編號" in df.columns
        assert "名字" in df.columns
        assert "作答email" in df.columns

    @patch("import_resume.drivers.lrs.requests.get")
    def test_fetch_data_request_error(self, mock_get):
        """Test handling of request errors."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        importer = LRSImporter()

        with pytest.raises(
            ImportError, match="Failed to fetch data from LRS Google Sheets"
        ):
            importer.fetch_data()

    def test_apply_source_specific_transforms_interview_status(self):
        """Test interview status transformations."""
        importer = LRSImporter()

        # Test "是" -> SCHEDULED
        row_dict = {"interview_status": "是"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.SCHEDULED

        # Test "約面" -> SCHEDULED
        row_dict = {"interview_status": "約面"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.SCHEDULED

        # Test "否" -> NOT_SCHEDULED
        row_dict = {"interview_status": "否"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.NOT_SCHEDULED

        # Test unknown value -> PENDING
        row_dict = {"interview_status": "待定"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.PENDING

    def test_apply_source_specific_transforms_source_id(self):
        """Test source ID conversion to string."""
        importer = LRSImporter()

        row_dict = {"source_id": 123}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["source_id"] == "123"
        assert isinstance(result["source_id"], str)

    def test_apply_source_specific_transforms_empty_strings(self):
        """Test empty string cleanup."""
        importer = LRSImporter()

        row_dict = {
            "full_name": "張三",
            "email": "",
            "recruiter_notes": "   ",
            "test_score": 85,
        }

        result = importer.apply_source_specific_transforms(row_dict)

        assert result["full_name"] == "張三"
        assert result["email"] is None
        assert result["recruiter_notes"] is None
        assert result["test_score"] == 85

    def test_transform_data(self, sample_lrs_dataframe):
        """Test data transformation with field mapping."""
        importer = LRSImporter()
        transformed_df = importer.transform_data(sample_lrs_dataframe)

        # Check that columns are mapped correctly
        expected_columns = [
            "source_id",
            "full_name",
            "email",
            "resume_file",
            "recruiter_notes",
            "test_url",
            "test_score",
            "interview_status",
            "hr_notes",
        ]

        for col in expected_columns:
            assert col in transformed_df.columns

        # Check data integrity
        assert len(transformed_df) == 3
        assert transformed_df["full_name"].iloc[0] == "張三"
        assert transformed_df["email"].iloc[0] == "zhang.san@example.com"

    @patch("import_resume.drivers.lrs.requests.get")
    def test_import_data_integration(
        self, mock_get, sample_lrs_csv_data, mock_requests_response
    ):
        """Test complete import data flow."""
        # Setup mock response
        mock_response = mock_requests_response(sample_lrs_csv_data)
        mock_get.return_value = mock_response

        importer = LRSImporter()
        result = importer.import_data(skip_validation=False)

        # Verify result structure
        assert result.success is True
        assert result.total_records == 3
        assert len(result.valid_resumes) > 0
        assert "LRS" in result.message

        # Verify resume data
        resume = result.valid_resumes[0]
        assert resume.full_name == "張三"
        assert resume.email == "zhang.san@example.com"
        assert resume.source == "lrs"
