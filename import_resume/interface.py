"""
Interface definitions for resume importers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .models import Resume, ResumeValidationError


@dataclass
class ImportResult:
    """Result of an import operation"""

    success: bool
    valid_resumes: list[Resume]
    validation_errors: list[ResumeValidationError]
    total_records: int
    message: str


class ResumeImporter(ABC):
    """
    Abstract base class for resume importers.

    Each source (LRS, LinkedIn, HR, etc.) should implement this interface.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def get_field_mapping(self) -> dict[str, str]:
        """
        Return mapping from source-specific field names to Resume model fields.

        Returns:
            Dict mapping source field names to Resume model field names
        """

    @abstractmethod
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """
        Fetch raw data from the source.

        Args:
            **kwargs: Source-specific parameters

        Returns:
            DataFrame with raw data from source

        Raises:
            ImportError: If data cannot be fetched
        """

    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform source data to match Resume model fields.

        Args:
            df: Raw data from source

        Returns:
            DataFrame with transformed field names
        """
        mapping = self.get_field_mapping()

        # Create new DataFrame with mapped columns
        transformed_data = {}

        for source_field, model_field in mapping.items():
            if source_field in df.columns:
                transformed_data[model_field] = df[source_field]

        # Handle NaN values
        transformed_df = pd.DataFrame(transformed_data)
        for col in transformed_df.columns:
            transformed_df[col] = transformed_df[col].where(
                pd.notna(transformed_df[col]), None
            )

        return transformed_df

    def validate_data(
        self, df: pd.DataFrame
    ) -> tuple[list[Resume], list[ResumeValidationError]]:
        """
        Validate transformed data and create Resume objects.

        Args:
            df: Transformed DataFrame

        Returns:
            Tuple of (valid_resumes, validation_errors)
        """
        valid_resumes = []
        validation_errors = []

        for index, row in df.iterrows():
            try:
                row_dict = row.to_dict()

                # Add source information
                row_dict["source"] = self.source_name.lower()

                # Apply source-specific transformations
                row_dict = self.apply_source_specific_transforms(row_dict)

                # Create Resume instance
                resume = Resume(**row_dict)

                # Only include complete resumes
                if resume.is_complete():
                    valid_resumes.append(resume)

            except Exception as e:
                validation_error = ResumeValidationError(
                    row_index=index,
                    field="general",
                    error=str(e),
                    raw_value=str(row_dict),
                )
                validation_errors.append(validation_error)

        return valid_resumes, validation_errors

    def apply_source_specific_transforms(
        self, row_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply source-specific data transformations.

        Override this method in subclasses for source-specific logic.

        Args:
            row_dict: Dictionary of row data

        Returns:
            Transformed row dictionary
        """
        return row_dict

    def import_data(self, skip_validation: bool = False, **kwargs) -> ImportResult:
        """
        Complete import process: fetch, transform, validate.

        Args:
            skip_validation: Whether to skip validation
            **kwargs: Source-specific parameters

        Returns:
            ImportResult with operation details
        """
        try:
            # Fetch raw data
            raw_df = self.fetch_data(**kwargs)

            # Transform data
            transformed_df = self.transform_data(raw_df)

            if skip_validation:
                # Create Resume objects without validation
                valid_resumes = []
                validation_errors = []

                for _index, row in transformed_df.iterrows():
                    try:
                        row_dict = row.to_dict()
                        row_dict["source"] = self.source_name.lower()
                        row_dict = self.apply_source_specific_transforms(row_dict)
                        resume = Resume(**row_dict)
                        valid_resumes.append(resume)
                    except Exception:  # nosec B112
                        continue  # Skip invalid rows when validation is disabled
            else:
                # Validate data
                valid_resumes, validation_errors = self.validate_data(transformed_df)

            return ImportResult(
                success=True,
                valid_resumes=valid_resumes,
                validation_errors=validation_errors,
                total_records=len(raw_df),
                message=f"Successfully processed {len(valid_resumes)} records from {self.source_name}",
            )

        except Exception as e:
            return ImportResult(
                success=False,
                valid_resumes=[],
                validation_errors=[],
                total_records=0,
                message=f"Failed to import from {self.source_name}: {str(e)}",
            )
