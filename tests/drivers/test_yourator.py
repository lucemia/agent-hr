"""Tests for Yourator importer."""

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from import_resume.drivers.yourator import YouratorImporter
from import_resume.models import ApplicationStatus


class TestYouratorImporter:
    """Test cases for Yourator importer."""

    def test_init(self):
        """Test Yourator importer initialization."""
        importer = YouratorImporter()
        assert importer.source_name == "Yourator"
        assert importer.file_path == "./yourator.xlsx"

    def test_get_field_mapping(self):
        """Test field mapping configuration."""
        importer = YouratorImporter()
        mapping = importer.get_field_mapping()

        expected_mappings = {
            "投遞編號": "source_id",
            "求職者姓名": "full_name",
            "求職者信箱": "email",
            "求職者電話": "phone",
            "職位名稱": "position_applied",
            "投遞時間": "application_date",
            "投遞狀態": "application_status",
            "履歷連結": "resume_file",
            "簡介": "recruiter_notes",
            "學歷一": "technical_notes",
            "工作經歷一": "hr_notes",
        }

        assert mapping == expected_mappings

    @patch("import_resume.drivers.yourator.pd.read_excel")
    @patch("import_resume.drivers.yourator.Path.exists")
    def test_fetch_data_success(self, mock_exists, mock_read_excel):
        """Test successful data fetching from Excel file."""
        # Setup mocks
        mock_exists.return_value = True
        sample_df = pd.DataFrame(
            {
                "投遞編號": ["abc123", "def456"],
                "求職者姓名": ["張三", "李四"],
                "求職者信箱": ["zhang@example.com", "li@example.com"],
            }
        )
        mock_read_excel.return_value = sample_df

        importer = YouratorImporter()
        df = importer.fetch_data()

        # Verify file existence check
        mock_exists.assert_called_once()

        # Verify Excel reading
        mock_read_excel.assert_called_once()

        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "投遞編號" in df.columns
        assert "求職者姓名" in df.columns

    @patch("import_resume.drivers.yourator.Path.exists")
    def test_fetch_data_file_not_found(self, mock_exists):
        """Test handling of missing Excel file."""
        mock_exists.return_value = False

        importer = YouratorImporter()

        with pytest.raises(ImportError, match="Excel file not found"):
            importer.fetch_data()

    @patch("import_resume.drivers.yourator.pd.read_excel")
    @patch("import_resume.drivers.yourator.Path.exists")
    def test_fetch_data_read_error(self, mock_exists, mock_read_excel):
        """Test handling of Excel read errors."""
        mock_exists.return_value = True
        mock_read_excel.side_effect = Exception("Excel read error")

        importer = YouratorImporter()

        with pytest.raises(ImportError, match="Failed to read Yourator Excel file"):
            importer.fetch_data()

    def test_fetch_data_custom_file_path(self):
        """Test fetch data with custom file path."""
        importer = YouratorImporter()

        with (
            patch("import_resume.drivers.yourator.Path.exists") as mock_exists,
            patch("import_resume.drivers.yourator.pd.read_excel") as mock_read_excel,
        ):
            mock_exists.return_value = True
            mock_read_excel.return_value = pd.DataFrame({"test": ["data"]})

            custom_path = "/custom/path/data.xlsx"
            importer.fetch_data(file_path=custom_path)

            # Verify custom path was used
            mock_exists.assert_called_once()
            call_args = mock_exists.call_args[0][0]
            assert str(call_args) == custom_path

    def test_apply_source_specific_transforms_application_date(self):
        """Test application date parsing."""
        importer = YouratorImporter()

        # Test valid datetime string
        row_dict = {"application_date": "2025-05-05 16:38:29"}
        result = importer.apply_source_specific_transforms(row_dict)
        expected_date = datetime(2025, 5, 5, 16, 38, 29)
        assert result["application_date"] == expected_date

        # Test invalid datetime string
        row_dict = {"application_date": "invalid-date"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["application_date"] is None

        # Test None value
        row_dict = {"application_date": None}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["application_date"] is None

    def test_apply_source_specific_transforms_application_status(self):
        """Test application status transformations."""
        importer = YouratorImporter()

        # Test "待審核" -> APPLIED
        row_dict = {"application_status": "待審核"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["application_status"] == ApplicationStatus.APPLIED

        # Test "審核中" -> SCREENING
        row_dict = {"application_status": "審核中"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["application_status"] == ApplicationStatus.SCREENING

        # Test "面試" -> INTERVIEW
        row_dict = {"application_status": "面試"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["application_status"] == ApplicationStatus.INTERVIEW

        # Test "錄取" -> HIRED
        row_dict = {"application_status": "錄取"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["application_status"] == ApplicationStatus.HIRED

        # Test "拒絕" -> REJECTED
        row_dict = {"application_status": "拒絕"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["application_status"] == ApplicationStatus.REJECTED

        # Test unknown status -> APPLIED (default)
        row_dict = {"application_status": "未知狀態"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["application_status"] == ApplicationStatus.APPLIED

    def test_apply_source_specific_transforms_phone_cleanup(self):
        """Test phone number formatting cleanup."""
        importer = YouratorImporter()

        # Test formatted phone number
        row_dict = {"phone": "(510) 918-5299"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["phone"] == "5109185299"

        # Test phone with spaces and dashes
        row_dict = {"phone": "02-1234-5678"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["phone"] == "021234567"

        # Test empty phone
        row_dict = {"phone": ""}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["phone"] is None

        # Test phone with only formatting characters
        row_dict = {"phone": "()- "}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["phone"] is None

    def test_apply_source_specific_transforms_source_id(self):
        """Test source ID conversion to string."""
        importer = YouratorImporter()

        row_dict = {"source_id": "be753a916f6e54f59bebd300887de2c6"}
        result = importer.apply_source_specific_transforms(row_dict)
        assert result["source_id"] == "be753a916f6e54f59bebd300887de2c6"
        assert isinstance(result["source_id"], str)

    def test_apply_source_specific_transforms_nan_and_empty_strings(self):
        """Test NaN and empty string cleanup."""
        importer = YouratorImporter()

        row_dict = {
            "full_name": "Ian Lin",
            "email": "",
            "phone": "   ",
            "recruiter_notes": pd.NA,
            "technical_notes": None,
        }

        result = importer.apply_source_specific_transforms(row_dict)

        assert result["full_name"] == "Ian Lin"
        assert result["email"] is None
        assert result["phone"] is None
        assert result["recruiter_notes"] is None
        assert result["technical_notes"] is None

    def test_transform_data(self):
        """Test data transformation with field mapping."""
        importer = YouratorImporter()

        # Create sample DataFrame with Yourator columns
        df = pd.DataFrame(
            {
                "投遞編號": ["abc123", "def456"],
                "求職者姓名": ["張三", "李四"],
                "求職者信箱": ["zhang@example.com", "li@example.com"],
                "職位名稱": ["軟體工程師", "資料工程師"],
                "投遞狀態": ["待審核", "審核中"],
            }
        )

        transformed_df = importer.transform_data(df)

        # Check that columns are mapped correctly
        expected_columns = [
            "source_id",
            "full_name",
            "email",
            "position_applied",
            "application_status",
        ]

        for col in expected_columns:
            assert col in transformed_df.columns

        # Check data integrity
        assert len(transformed_df) == 2
        assert transformed_df["full_name"].iloc[0] == "張三"
        assert transformed_df["email"].iloc[0] == "zhang@example.com"
        assert transformed_df["position_applied"].iloc[0] == "軟體工程師"

    @patch("import_resume.drivers.yourator.pd.read_excel")
    @patch("import_resume.drivers.yourator.Path.exists")
    def test_import_data_integration(self, mock_exists, mock_read_excel):
        """Test complete import data flow."""
        # Setup mocks
        mock_exists.return_value = True
        sample_df = pd.DataFrame(
            {
                "投遞編號": ["abc123"],
                "求職者姓名": ["張三"],
                "求職者信箱": ["zhang@example.com"],
                "求職者電話": ["0912345678"],
                "職位名稱": ["軟體工程師"],
                "投遞時間": ["2025-05-05 16:38:29"],
                "投遞狀態": ["待審核"],
                "履歷連結": ["https://example.com/resume"],
                "簡介": ["優秀的軟體工程師"],
            }
        )
        mock_read_excel.return_value = sample_df

        importer = YouratorImporter()
        result = importer.import_data(skip_validation=False)

        # Verify result structure
        assert result.success is True
        assert result.total_records == 1
        assert len(result.valid_resumes) == 1
        assert "Yourator" in result.message

        # Verify resume data
        resume = result.valid_resumes[0]
        assert resume.full_name == "張三"
        assert resume.email == "zhang@example.com"
        assert resume.phone == "0912345678"
        assert resume.position_applied == "軟體工程師"
        assert resume.application_status == ApplicationStatus.APPLIED
        assert resume.source == "yourator"

    def test_datetime_edge_cases(self):
        """Test edge cases for datetime parsing."""
        importer = YouratorImporter()

        # Test different datetime formats
        test_cases = [
            ("2025-01-01 00:00:00", datetime(2025, 1, 1, 0, 0, 0)),
            ("2025-12-31 23:59:59", datetime(2025, 12, 31, 23, 59, 59)),
            ("invalid-date", None),
            ("", None),
            (None, None),
        ]

        for input_date, expected_output in test_cases:
            row_dict = {"application_date": input_date}
            result = importer.apply_source_specific_transforms(row_dict)
            assert result["application_date"] == expected_output

    def test_application_status_edge_cases(self):
        """Test edge cases for application status mapping."""
        importer = YouratorImporter()

        # Test English equivalents
        test_cases = [
            ("pending", ApplicationStatus.APPLIED),
            ("submitted", ApplicationStatus.APPLIED),
            ("reviewing", ApplicationStatus.SCREENING),
            ("screening", ApplicationStatus.SCREENING),
            ("interview", ApplicationStatus.INTERVIEW),
            ("interviewing", ApplicationStatus.INTERVIEW),
            ("hired", ApplicationStatus.HIRED),
            ("accepted", ApplicationStatus.HIRED),
            ("rejected", ApplicationStatus.REJECTED),
            ("declined", ApplicationStatus.REJECTED),
            ("unknown_status", ApplicationStatus.APPLIED),  # Default
        ]

        for input_status, expected_status in test_cases:
            row_dict = {"application_status": input_status}
            result = importer.apply_source_specific_transforms(row_dict)
            assert result["application_status"] == expected_status
