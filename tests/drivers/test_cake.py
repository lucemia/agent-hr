"""Tests for Cake importer."""

from unittest.mock import patch

import pandas as pd
import pytest

from import_resume.drivers.cake import CakeImporter
from import_resume.models import InterviewStatus


class TestCakeImporter:
    """Test cases for Cake importer."""

    def test_init(self):
        """Test Cake importer initialization."""
        importer = CakeImporter()
        assert importer.source_name == "Cake"
        assert "1hinp7M0dyMdL6bnoq4hRv4iHuwa9CuZzd8Xs8pdwoOo" in importer.sheet_url
        assert "gid=341040725" in importer.sheet_url

    def test_get_field_mapping(self):
        """Test field mapping configuration."""
        importer = CakeImporter()
        mapping = importer.get_field_mapping()

        expected_mappings = {
            "名字": "full_name",
            "email": "email",
            "分數": "test_score",
            "測驗結果": "test_url",
            "履歷": "resume_file",
            "是否約面": "interview_status",
            "是否約面.1": "interview_status_2",
            "職缺": "position_applied",
            "補充說明": "recruiter_notes",
            "Comment": "hr_notes",
            "FROM": "source_id",
        }

        assert mapping == expected_mappings

    @patch("import_resume.drivers.cake.requests.get")
    def test_fetch_data_success(
        self, mock_get, sample_cake_csv_data, mock_requests_response
    ):
        """Test successful data fetching."""
        # Setup mock response
        mock_response = mock_requests_response(sample_cake_csv_data)
        mock_get.return_value = mock_response

        importer = CakeImporter()
        df = importer.fetch_data()

        # Verify request was made correctly
        mock_get.assert_called_once_with(importer.sheet_url, timeout=30)

        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "名字" in df.columns
        assert "email" in df.columns
        assert "分數" in df.columns

    @patch("import_resume.drivers.cake.requests.get")
    def test_fetch_data_request_error(self, mock_get):
        """Test handling of request errors."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        importer = CakeImporter()

        with pytest.raises(
            ImportError, match="Failed to fetch data from Cake Google Sheets"
        ):
            importer.fetch_data()

    def test_apply_source_specific_transforms_test_score_percentage(self):
        """Test test score percentage conversion."""
        importer = CakeImporter()

        # Test percentage string conversion
        row_dict = {"test_score": "69%"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["test_score"] == 69.0

        # Test regular number
        row_dict = {"test_score": "85"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["test_score"] == 85.0

        # Test invalid value
        row_dict = {"test_score": "invalid"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["test_score"] is None

    def test_apply_source_specific_transforms_interview_status_boolean(self):
        """Test interview status boolean conversion."""
        importer = CakeImporter()

        # Test True -> SCHEDULED
        row_dict = {"interview_status": True}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.SCHEDULED

        # Test False -> NOT_SCHEDULED
        row_dict = {"interview_status": False}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.NOT_SCHEDULED

    def test_apply_source_specific_transforms_interview_status_string(self):
        """Test interview status string conversion."""
        importer = CakeImporter()

        # Test "true" -> SCHEDULED
        row_dict = {"interview_status": "true"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.SCHEDULED

        # Test "false" -> NOT_SCHEDULED
        row_dict = {"interview_status": "false"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.NOT_SCHEDULED

        # Test "是" -> SCHEDULED
        row_dict = {"interview_status": "是"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.SCHEDULED

    def test_apply_source_specific_transforms_interview_status_backup_field(self):
        """Test interview status backup field handling."""
        importer = CakeImporter()

        # Test backup field when primary is None
        row_dict = {"interview_status": None, "interview_status_2": True}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["interview_status"] == InterviewStatus.SCHEDULED
        assert "interview_status_2" not in result  # Should be removed

    def test_apply_source_specific_transforms_source_id(self):
        """Test source ID conversion to string."""
        importer = CakeImporter()

        row_dict = {"source_id": "cake"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["source_id"] == "cake"
        assert isinstance(result["source_id"], str)

    def test_apply_source_specific_transforms_empty_strings(self):
        """Test empty string cleanup."""
        importer = CakeImporter()

        row_dict = {
            "full_name": "Sidney Lu",
            "email": "",
            "recruiter_notes": "   ",
            "test_score": "69%",
        }

        result = importer.apply_source_specific_transforms(row_dict)

        assert result["full_name"] == "Sidney Lu"
        assert result["email"] is None
        assert result["recruiter_notes"] is None
        assert result["test_score"] == 69.0

    def test_transform_data(self, sample_cake_dataframe):
        """Test data transformation with field mapping."""
        importer = CakeImporter()
        transformed_df = importer.transform_data(sample_cake_dataframe)

        # Check that columns are mapped correctly
        expected_columns = [
            "full_name",
            "email",
            "test_score",
            "test_url",
            "resume_file",
            "interview_status",
            "interview_status_2",
            "position_applied",
            "recruiter_notes",
            "hr_notes",
            "source_id",
        ]

        for col in expected_columns:
            if col in sample_cake_dataframe.columns or importer.get_field_mapping().get(
                col
            ):
                assert col in transformed_df.columns or any(
                    importer.get_field_mapping().get(orig_col) == col
                    for orig_col in sample_cake_dataframe.columns
                )

        # Check data integrity
        assert len(transformed_df) == 3
        assert transformed_df["full_name"].iloc[0] == "Sidney Lu"
        assert transformed_df["email"].iloc[0] == "sidney@example.com"

    @patch("import_resume.drivers.cake.requests.get")
    def test_import_data_integration(
        self, mock_get, sample_cake_csv_data, mock_requests_response
    ):
        """Test complete import data flow."""
        # Setup mock response
        mock_response = mock_requests_response(sample_cake_csv_data)
        mock_get.return_value = mock_response

        importer = CakeImporter()
        result = importer.import_data(skip_validation=False)

        # Verify result structure
        assert result.success is True
        assert result.total_records == 3
        assert len(result.valid_resumes) > 0
        assert "Cake" in result.message

        # Verify resume data
        resume = result.valid_resumes[0]
        assert resume.full_name == "Sidney Lu"
        assert resume.email == "sidney@example.com"
        assert resume.source == "cake"

    def test_percentage_edge_cases(self):
        """Test edge cases for percentage conversion."""
        importer = CakeImporter()

        # Test empty percentage
        row_dict = {"test_score": "%"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["test_score"] is None

        # Test zero percentage
        row_dict = {"test_score": "0%"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["test_score"] == 0.0

        # Test 100 percentage
        row_dict = {"test_score": "100%"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["test_score"] == 100.0
