"""
Cake (Google Sheets) resume importer implementation.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from ..interface import ResumeImporter
from ..models import InterviewStatus
from .utils import get_hyperlinks_from_worksheet

logger = logging.getLogger(__name__)

try:
    import gspread

    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


class CakeImporter(ResumeImporter):
    """
    Importer for Cake Google Sheets data.

    Handles the specific field mappings and data transformations
    required for the Cake Google Sheets source.
    """

    def __init__(self):
        super().__init__("Cake")
        self.sheet_id = "1hinp7M0dyMdL6bnoq4hRv4iHuwa9CuZzd8Xs8pdwoOo"
        # No longer using a single gid - we'll fetch all worksheets

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
            "position_applied": "position_applied",  # Preserve position_applied from worksheet title
        }

    def _get_gspread_client(self):
        """Get gspread client with credentials."""
        import os

        import gspread

        # Check for credentials in multiple locations
        cred_path = None

        # 1. Check environment variable
        env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if env_path and Path(env_path).exists():
            cred_path = Path(env_path)

        # 2. Check default location
        if not cred_path:
            default_path = Path.home() / ".config" / "gspread" / "service_account.json"
            if default_path.exists():
                cred_path = default_path

        # 3. Try to load from .env file if it exists
        if not cred_path:
            env_file = Path.cwd() / ".env"
            if env_file.exists():
                try:
                    with open(env_file) as f:
                        for line in f:
                            if line.startswith("GOOGLE_APPLICATION_CREDENTIALS"):
                                env_value = (
                                    line.split("=", 1)[1].strip().strip('"').strip("'")
                                )
                                if Path(env_value).exists():
                                    cred_path = Path(env_value)
                                    break
                except Exception:
                    pass

        # Use credentials if found
        if cred_path:
            return gspread.service_account(filename=str(cred_path))
        else:
            return gspread.service_account()

    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """
        Fetch data from all worksheets in Cake Google Sheets.
        Each worksheet represents a different job position.

        Returns:
            DataFrame with raw Cake data from all worksheets, with position_applied set to worksheet title

        Raises:
            ImportError: If credentials are not available or data cannot be fetched
        """
        if not GSPREAD_AVAILABLE:
            raise ImportError(
                "gspread is required for Cake import. Install it with: uv add gspread"
            )

        try:
            gc = self._get_gspread_client()
        except Exception as e:
            raise ImportError(
                "Google service account credentials not found. "
                "To import from Cake Google Sheets, you must set up credentials.\n"
                "Options:\n"
                "  1. Place credentials at: ~/.config/gspread/service_account.json\n"
                "  2. Set environment variable: GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json\n"
                "  3. Add to .env file: GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json\n"
                "  4. Run setup script: uv run python setup_google_credentials.py\n"
                f"Error: {e}"
            )

        # Open the sheet and get all worksheets
        sheet = gc.open_by_key(self.sheet_id)
        worksheets = sheet.worksheets()

        all_dfs = []

        for worksheet in worksheets:
            worksheet_title = worksheet.title
            logger.info(f"Fetching data from worksheet: {worksheet_title}")

            try:
                # Get all values from the worksheet
                values = worksheet.get_all_values()

                if not values or len(values) < 2:  # Need at least header + 1 data row
                    logger.debug(f"No data in worksheet '{worksheet_title}'")
                    continue

                # Convert to DataFrame
                headers = values[0]
                data_rows = values[1:]

                # Handle duplicate column names by adding suffix
                # pandas automatically handles duplicates by adding .1, .2, etc.
                # But we need to handle them manually to match our field mapping
                seen = {}
                unique_headers = []
                header_mapping = {}  # Map unique headers back to original names for field mapping

                for h in headers:
                    if h in seen:
                        seen[h] += 1
                        unique_name = (
                            f"{h}.{seen[h]}"  # Use . notation to match pandas default
                        )
                        unique_headers.append(unique_name)
                        header_mapping[unique_name] = h
                    else:
                        seen[h] = 0
                        unique_headers.append(h)
                        header_mapping[h] = h

                df = pd.DataFrame(data_rows, columns=unique_headers)

                # Add position_applied column with worksheet title
                # Note: If the sheet already has a "職缺" column, this will override it with the worksheet title
                # This ensures consistency - the worksheet name is the job position
                df["position_applied"] = worksheet_title

                # Try to enhance resume_file column with hyperlinks if available
                if "履歷" in df.columns:
                    # Extract hyperlinks from this worksheet
                    try:
                        hyperlinks = self._get_hyperlinks(worksheet, worksheet_title)

                        if hyperlinks:
                            logger.info(
                                f"Found {len(hyperlinks)} hyperlinks in '{worksheet_title}'"
                            )

                        # Replace filename values with URLs where hyperlinks are available
                        for idx, url in hyperlinks.items():
                            if idx < len(df):
                                df.iloc[idx, df.columns.get_loc("履歷")] = url
                    except Exception as e:
                        logger.debug(
                            f"Could not extract hyperlinks from '{worksheet_title}': {e}"
                        )

                all_dfs.append(df)

            except Exception as e:
                logger.warning(
                    f"Failed to fetch data from worksheet '{worksheet_title}': {e}"
                )
                continue

        if not all_dfs:
            raise ImportError("No data found in any worksheet")

        # Combine all DataFrames
        # Use outer join to handle different column structures across worksheets
        combined_df = pd.concat(all_dfs, ignore_index=True, sort=False)

        logger.info(
            f"Combined data from {len(all_dfs)} worksheets: {[ws.title for ws in worksheets if len(ws.get_all_values()) > 1]}"
        )

        return combined_df

    def _get_hyperlinks(self, worksheet, worksheet_title: str) -> dict[int, str]:
        """
        Get hyperlinks from a specific Google Sheets worksheet.

        Args:
            worksheet: gspread worksheet object
            worksheet_title: Title of the worksheet (for logging)

        Returns:
            Dictionary mapping row index (0-based, excluding header) to URL string
        """
        if not GSPREAD_AVAILABLE:
            return {}

        try:
            # Find which column contains 履歷 (resume_file)
            headers = worksheet.row_values(1)
            try:
                resume_col_idx = (
                    headers.index("履歷") + 1
                )  # gspread uses 1-based indexing
            except ValueError:
                logger.debug(f"履歷 column not found in worksheet '{worksheet_title}'")
                return {}

            # Use column index mode for Cake
            return get_hyperlinks_from_worksheet(
                worksheet=worksheet,
                sheet_id=self.sheet_id,
                column_index=resume_col_idx,
                worksheet_title=worksheet_title,
            )
        except Exception as e:
            logger.debug(f"Could not extract hyperlinks from '{worksheet_title}': {e}")
            return {}

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
