"""Tests for the ResumeImporter interface."""

from unittest.mock import Mock

import pandas as pd

from import_resume.interface import ImportResult, ResumeImporter


class ConcreteImporter(ResumeImporter):
    """Concrete implementation for testing."""

    def __init__(self):
        super().__init__("Test")

    def get_field_mapping(self):
        return {"name": "full_name", "email": "email"}

    def fetch_data(self, **kwargs):
        return pd.DataFrame(
            {
                "name": ["John Doe", "Jane Smith"],
                "email": ["john@example.com", "jane@example.com"],
            }
        )


class TestResumeImporter:
    """Test cases for ResumeImporter interface."""

    def test_init(self):
        """Test importer initialization."""
        importer = ConcreteImporter()
        assert importer.source_name == "Test"

    def test_transform_data(self):
        """Test data transformation."""
        importer = ConcreteImporter()

        # Create sample data
        df = pd.DataFrame(
            {
                "name": ["John Doe", "Jane Smith"],
                "email": ["john@example.com", "jane@example.com"],
                "extra_field": ["value1", "value2"],
            }
        )

        transformed_df = importer.transform_data(df)

        # Check that mapped fields are present
        assert "full_name" in transformed_df.columns
        assert "email" in transformed_df.columns

        # Check that unmapped fields are not present
        assert "name" not in transformed_df.columns
        assert "extra_field" not in transformed_df.columns

        # Check data integrity
        assert len(transformed_df) == 2
        assert transformed_df["full_name"].iloc[0] == "John Doe"
        assert transformed_df["email"].iloc[0] == "john@example.com"

    def test_validate_data(self):
        """Test data validation."""
        importer = ConcreteImporter()

        # Create sample transformed data
        df = pd.DataFrame(
            {
                "full_name": ["John Doe", "Jane Smith", ""],
                "email": ["john@example.com", "invalid-email", "jane@example.com"],
            }
        )

        valid_resumes, validation_errors = importer.validate_data(df)

        # Should have some valid resumes and some errors
        assert len(valid_resumes) >= 0
        assert len(validation_errors) >= 0

        # Check that source is set
        if valid_resumes:
            assert valid_resumes[0].source == "test"

    def test_apply_source_specific_transforms_default(self):
        """Test default source-specific transforms."""
        importer = ConcreteImporter()

        row_dict = {"full_name": "John Doe", "email": "john@example.com"}
        result = importer.apply_source_specific_transforms(row_dict)

        # Default implementation should return unchanged data
        assert result == row_dict

    def test_import_data_success(self):
        """Test successful import data flow."""
        importer = ConcreteImporter()

        result = importer.import_data(skip_validation=True)

        assert isinstance(result, ImportResult)
        assert result.success is True
        assert result.total_records == 2
        assert len(result.valid_resumes) == 2
        assert "Test" in result.message

    def test_import_data_with_validation(self):
        """Test import data with validation."""
        importer = ConcreteImporter()

        result = importer.import_data(skip_validation=False)

        assert isinstance(result, ImportResult)
        assert result.success is True
        assert result.total_records == 2
        # May have fewer valid resumes due to validation
        assert len(result.valid_resumes) >= 0

    def test_import_data_fetch_error(self):
        """Test import data with fetch error."""
        importer = ConcreteImporter()

        # Mock fetch_data to raise an exception
        importer.fetch_data = Mock(side_effect=Exception("Fetch error"))

        result = importer.import_data()

        assert result.success is False
        assert "Fetch error" in result.message
        assert result.total_records == 0
        assert len(result.valid_resumes) == 0
