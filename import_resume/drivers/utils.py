"""
Utility functions for Google Sheets importers.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_hyperlink_from_cell(cell: dict[str, Any], row_idx: int) -> str | None:
    """
    Extract hyperlink URL from a Google Sheets cell using multiple methods.
    
    Checks for hyperlinks in the following order:
    1. Direct hyperlink property
    2. HYPERLINK formula in userEnteredValue
    3. effectiveValue hyperlink
    4. Drive file smart chips (chipRuns)
    5. textFormatRuns (formatted text links)
    
    Args:
        cell: Cell data from Google Sheets API response
        row_idx: Row index (0-based, excluding header) for logging
        
    Returns:
        URL string if found, None otherwise
    """
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
            # Extract URL from HYPERLINK formula
            # HYPERLINK("url", "display text") or HYPERLINK("url")
            match = re.search(r'HYPERLINK\("([^"]+)"', formula)
            if match:
                url = match.group(1)
                logger.debug(f"Found HYPERLINK formula in userEnteredValue in row {row_idx + 2}: {url}")
    
    # Method 3: Check effectiveValue for hyperlink
    if not url and 'effectiveValue' in cell:
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
    
    return url


def parse_api_response(response: Any) -> dict[str, Any]:
    """
    Parse Google Sheets API response, handling both dict and Response objects.
    
    Args:
        response: Response from gspread client.request()
        
    Returns:
        Parsed response as dictionary
    """
    if isinstance(response, dict):
        return response
    elif hasattr(response, 'json'):
        return response.json()
    elif hasattr(response, 'text'):
        return json.loads(response.text)
    else:
        return response


def get_hyperlinks_from_worksheet(
    worksheet: Any,
    sheet_id: str,
    column_range: str | None = None,
    column_index: int | None = None,
    worksheet_title: str | None = None,
) -> dict[int, str]:
    """
    Get hyperlinks from a Google Sheets worksheet column.
    
    Supports two modes:
    1. Column range mode: Specify a column range like "D:D" to fetch only that column
    2. Column index mode: Fetch full worksheet and extract specific column by index
    
    Args:
        worksheet: gspread worksheet object
        sheet_id: Google Sheets spreadsheet ID
        column_range: Column range (e.g., "D:D") - if provided, uses range mode
        column_index: Column index (1-based) - if provided, uses index mode
        worksheet_title: Title of the worksheet (for logging)
        
    Returns:
        Dictionary mapping row index (0-based, excluding header) to URL string
    """
    hyperlinks = {}
    
    if worksheet_title is None:
        worksheet_title = worksheet.title
    
    try:
        sheet_obj = worksheet.spreadsheet
        
        # Determine which mode to use
        if column_range:
            # Range mode: fetch specific column range
            range_str = f"{worksheet.title}!{column_range}"
            logger.debug(f"Fetching hyperlinks from range '{range_str}' in worksheet '{worksheet_title}'")
        else:
            # Index mode: fetch full worksheet
            range_str = worksheet.title
            if column_index:
                logger.debug(f"Fetching hyperlinks from column {column_index} (1-based) in worksheet '{worksheet_title}'")
            else:
                logger.debug(f"Fetching hyperlinks from worksheet '{worksheet_title}'")
        
        # Get the spreadsheet data with hyperlinks
        # Request more fields to capture hyperlinks from formulas, effectiveValue, textFormatRuns, and chipRuns
        response = sheet_obj.client.request(
            "get",
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}",
            params={
                "ranges": range_str,
                "includeGridData": "true",
                "fields": "sheets(data(rowData(values(hyperlink,effectiveValue,userEnteredValue,textFormatRuns,chipRuns))))"
            }
        )
        
        # Parse response
        result = parse_api_response(response)
        logger.debug(f"API response type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        
        if result and 'sheets' in result and len(result['sheets']) > 0:
            sheet_data = result['sheets'][0]
            if 'data' in sheet_data and len(sheet_data['data']) > 0:
                row_data = sheet_data['data'][0].get('rowData', [])
                logger.debug(f"Found {len(row_data)} rows in worksheet '{worksheet_title}'")
                
                # Skip header row (index 0), start from row 1
                for row_idx, row in enumerate(row_data[1:], start=0):
                    if row and 'values' in row and len(row['values']) > 0:
                        # Determine which cell to check based on mode
                        if column_range:
                            # Range mode: first (and only) column in the range
                            cell = row['values'][0]
                        elif column_index:
                            # Index mode: specific column by index
                            if len(row['values']) >= column_index:
                                cell = row['values'][column_index - 1]
                            else:
                                continue
                        else:
                            # Default: first column
                            cell = row['values'][0]
                        
                        # Extract hyperlink from cell
                        url = extract_hyperlink_from_cell(cell, row_idx)
                        if url:
                            hyperlinks[row_idx] = url
                            
    except Exception as e:
        logger.warning(f"Failed to extract hyperlinks from worksheet '{worksheet_title}': {e}")
    
    return hyperlinks

