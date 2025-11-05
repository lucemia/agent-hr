"""
LRS (Google Sheets) resume importer implementation.
"""

import logging
from io import StringIO
from typing import Any

import pandas as pd
import requests

from ..interface import ResumeImporter
from ..models import InterviewStatus

logger = logging.getLogger(__name__)

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


def _col_idx_to_letter(col_idx: int) -> str:
    """
    Convert 1-based column index to letter (A, B, ..., Z, AA, ...).

    Args:
        col_idx: 1-based column index

    Returns:
        Column letter (e.g., 'A', 'B', 'AA', 'AB')
    """
    result = ""
    while col_idx > 0:
        col_idx -= 1
        result = chr(65 + (col_idx % 26)) + result
        col_idx //= 26
    return result


class LRSImporter(ResumeImporter):
    """
    Importer for LRS Google Sheets data.

    Handles the specific field mappings and data transformations
    required for the LRS Google Sheets source.
    """

    def __init__(self):
        super().__init__("LRS")
        self.sheet_id = "1mGpl2LzdXZlrKYXatWdAKQrI5SsagjTEen58xtjDNms"
        # No longer using a single gid - we'll fetch all worksheets
        self._gspread_client = None

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
            "position_applied": "position_applied",  # Preserve position_applied from worksheet title
        }

    def _get_hyperlinks(self, worksheet, worksheet_title: str) -> dict[int, str]:
        """
        Get hyperlinks from a specific Google Sheets worksheet using gspread if available.
        Uses the Google Sheets API v4 to extract hyperlinks directly from cells.

        Args:
            worksheet: gspread worksheet object
            worksheet_title: Title of the worksheet (for logging)

        Returns:
            Dictionary mapping row index (0-based, excluding header) to URL string
        """
        hyperlinks = {}
        
        if not GSPREAD_AVAILABLE:
            logger.warning("gspread not available, cannot extract hyperlinks")
            return hyperlinks
            
        try:
            # Find which column contains 履歷 (resume_file)
            # Try header name first, then fallback to column D (index 4)
            headers = worksheet.row_values(1)
            resume_col_idx = None
            
            # Try to find by header name
            try:
                resume_col_idx = headers.index("履歷") + 1  # gspread uses 1-based indexing
                logger.debug(f"Found '履歷' column at index {resume_col_idx} in worksheet '{worksheet_title}'")
            except ValueError:
                # Column not found by header name, try column D (index 4)
                logger.debug(f"履歷 column not found by name in worksheet '{worksheet_title}', trying column D")
                resume_col_idx = 4  # Column D is index 4 (1-based)
            
            if resume_col_idx is None:
                logger.warning(f"Could not determine resume column for worksheet '{worksheet_title}'")
                return hyperlinks
            
            # Use the Google Sheets API v4 to get hyperlinks directly
            sheet_obj = worksheet.spreadsheet
            logger.debug(f"Fetching hyperlinks from column {resume_col_idx} (1-based) in worksheet '{worksheet_title}'")
            
            try:
                # Get the spreadsheet data with hyperlinks
                # Request more fields to capture hyperlinks from formulas, effectiveValue, textFormatRuns, and chipRuns (Drive file smart chips)
                response = sheet_obj.client.request(
                    "get",
                    f"https://sheets.googleapis.com/v4/spreadsheets/{self.sheet_id}",
                    params={
                        "ranges": f"{worksheet.title}!D:D",  # Explicitly request column D
                        "includeGridData": "true",
                        "fields": "sheets(data(rowData(values(hyperlink,effectiveValue,userEnteredValue,textFormatRuns,chipRuns))))"
                    }
                )
                
                # Parse response if it's a Response object
                # gspread's client.request() may return a dict or a Response object
                if isinstance(response, dict):
                    result = response
                elif hasattr(response, 'json'):
                    result = response.json()
                elif hasattr(response, 'text'):
                    import json
                    result = json.loads(response.text)
                else:
                    result = response
                
                logger.debug(f"API response type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
                
                if result and 'sheets' in result and len(result['sheets']) > 0:
                    sheet_data = result['sheets'][0]
                    if 'data' in sheet_data and len(sheet_data['data']) > 0:
                        row_data = sheet_data['data'][0].get('rowData', [])
                        logger.debug(f"Found {len(row_data)} rows in worksheet '{worksheet_title}'")
                        
                        # Skip header row (index 0), start from row 1
                        for row_idx, row in enumerate(row_data[1:], start=0):
                            if row and 'values' in row and len(row['values']) > 0:
                                # Column D is the first (and only) column in the range
                                cell = row['values'][0]
                                
                                url = None
                                
                                # Method 1: Check if cell has a direct hyperlink property
                                if 'hyperlink' in cell and cell['hyperlink']:
                                    url = cell['hyperlink']
                                    logger.debug(f"Found direct hyperlink in row {row_idx + 2}: {url}")
                                
                                # Method 2: Check if it's a HYPERLINK formula in userEnteredValue
                                if not url and 'userEnteredValue' in cell:
                                    user_value = cell['userEnteredValue']
                                    if 'formulaValue' in user_value:
                                        formula = user_value['formulaValue']
                                        import re
                                        # Extract URL from HYPERLINK formula
                                        # HYPERLINK("url", "display text") or HYPERLINK("url")
                                        match = re.search(r'HYPERLINK\("([^"]+)"', formula)
                                        if match:
                                            url = match.group(1)
                                            logger.debug(f"Found HYPERLINK formula in userEnteredValue in row {row_idx + 2}: {url}")
                                
                                # Method 3: Check effectiveValue for hyperlink
                                elif 'effectiveValue' in cell:
                                    eff_value = cell['effectiveValue']
                                    if 'hyperlink' in eff_value:
                                        url = eff_value['hyperlink']
                                        logger.debug(f"Found hyperlink in effectiveValue in row {row_idx + 2}: {url}")
                                
                                # Method 4: Check chipRuns for Drive file smart chips
                                if not url and 'chipRuns' in cell and cell['chipRuns']:
                                    for chip_run in cell['chipRuns']:
                                        if 'chip' in chip_run and 'richLinkProperties' in chip_run['chip']:
                                            rich_link = chip_run['chip']['richLinkProperties']
                                            if 'uri' in rich_link:
                                                url = rich_link['uri']
                                                logger.debug(f"Found Drive file smart chip in row {row_idx + 2}: {url}")
                                                break
                                
                                # Method 5: Check textFormatRuns for hyperlink (for formatted text with links)
                                if not url and 'textFormatRuns' in cell and cell['textFormatRuns']:
                                    for text_run in cell['textFormatRuns']:
                                        if 'link' in text_run and 'uri' in text_run['link']:
                                            url = text_run['link']['uri']
                                            logger.debug(f"Found hyperlink in textFormatRuns in row {row_idx + 2}: {url}")
                                            break
                                
                                if url:
                                    hyperlinks[row_idx] = url
                                            
            except Exception as e:
                logger.warning(f"Failed to extract hyperlinks using includeGridData method: {e}")
            
            # Always try alternative method using formulas as a fallback
            # Sometimes hyperlinks are stored as HYPERLINK formulas
            if not hyperlinks:
                try:
                    num_rows = len(worksheet.get_all_values())
                    if num_rows > 1:
                        col_letter = _col_idx_to_letter(resume_col_idx)
                        logger.debug(f"Trying alternative method with column {col_letter} (formula extraction)")
                        # Try to get formulas
                        response = sheet_obj.client.request(
                            "get",
                            f"https://sheets.googleapis.com/v4/spreadsheets/{self.sheet_id}/values/{worksheet.title}!{col_letter}2:{col_letter}{num_rows}",
                            params={"valueRenderOption": "FORMULA"}
                        )
                        
                        # Parse response if it's a Response object
                        if isinstance(response, dict):
                            result = response
                        elif hasattr(response, 'json'):
                            result = response.json()
                        elif hasattr(response, 'text'):
                            import json
                            result = json.loads(response.text)
                        else:
                            result = response
                        
                        if result and 'values' in result:
                            import re
                            for idx, row in enumerate(result['values']):
                                if row and len(row) > 0:
                                    formula = row[0]
                                    # Check for HYPERLINK formula
                                    # HYPERLINK("url", "display text") or HYPERLINK("url")
                                    match = re.search(r'HYPERLINK\("([^"]+)"', formula)
                                    if match:
                                        url = match.group(1)
                                        hyperlinks[idx] = url
                                        logger.debug(f"Found HYPERLINK formula via alternative method in row {idx + 2}: {url}")
                except Exception as e2:
                    logger.debug(f"Alternative method (formula extraction) also failed: {e2}")
                
        except Exception as e:
            logger.error(f"Error extracting hyperlinks from worksheet '{worksheet_title}': {e}", exc_info=True)
            
        logger.info(f"Extracted {len(hyperlinks)} hyperlinks from worksheet '{worksheet_title}'")
        return hyperlinks

    def _get_gspread_client(self):
        """Get gspread client with credentials."""
        import gspread
        import os
        from pathlib import Path
        
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
                                env_value = line.split("=", 1)[1].strip().strip('"').strip("'")
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
        Fetch data from all worksheets in LRS Google Sheets.
        Each worksheet represents a different job position.

        Returns:
            DataFrame with raw LRS data from all worksheets, with position_applied set to worksheet title

        Raises:
            ImportError: If credentials are not available or data cannot be fetched
        """
        if not GSPREAD_AVAILABLE:
            raise ImportError(
                "gspread is required for LRS import. "
                "Install it with: uv add gspread"
            )
        
        try:
            import gspread
            gc = self._get_gspread_client()
        except Exception as e:
            raise ImportError(
                "Google service account credentials not found. "
                "To import from LRS Google Sheets, you must set up credentials.\n"
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
                
                df = pd.DataFrame(data_rows, columns=headers)
                
                # Add position_applied column with worksheet title
                df["position_applied"] = worksheet_title
                
                # Try to enhance resume_file column with hyperlinks if available
                if "履歷" in df.columns:
                    hyperlinks = self._get_hyperlinks(worksheet, worksheet_title)
                    
                    if hyperlinks:
                        logger.info(f"Found {len(hyperlinks)} hyperlinks in '{worksheet_title}'")
                    
                    # Replace filename values with URLs where hyperlinks are available
                    # hyperlinks dict maps 0-based row index (excluding header) to URL
                    for idx, url in hyperlinks.items():
                        # idx is 0-based row index in the data (excluding header)
                        if idx < len(df):
                            # Update the resume_file value with the actual URL
                            df.iloc[idx, df.columns.get_loc("履歷")] = url
                
                all_dfs.append(df)
                
            except Exception as e:
                logger.warning(f"Failed to fetch data from worksheet '{worksheet_title}': {e}")
                continue
        
        if not all_dfs:
            raise ImportError("No data found in any worksheet")
        
        # Combine all DataFrames
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
        logger.info(f"Combined data from {len(all_dfs)} worksheets: {[ws.title for ws in worksheets if len(ws.get_all_values()) > 1]}")
        
        return combined_df

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
