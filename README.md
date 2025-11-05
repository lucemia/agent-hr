# Agent HR - Resume Import System

A modular resume import system that can import resume data from various sources (LRS, Cake, Yourator, CSV, etc.) into a unified SQLite database.

## Features

- **Multiple Import Sources**: Support for LRS, Cake, Yourator, CSV files
- **Automatic Resume File Backup**: Automatically backs up resume files when importing
- **Hyperlink Preservation**: Extracts URLs from Google Sheets hyperlinks (with credentials)
- **Data Validation**: Built-in validation for email, test scores, and other fields
- **Flexible Architecture**: Easy to add new import sources

## Quick Start

### Installation

```bash
# Install dependencies
uv sync

# Run an import
uv run python main.py import-resume lrs
```

### Setting Up Google Sheets Hyperlink Extraction

To preserve URLs from Google Sheets (instead of just filenames), you need to set up Google service account credentials:

```bash
# Run the interactive setup script
uv run python setup_google_credentials.py
```

Or follow the manual instructions in [HYPERLINK_SETUP.md](./HYPERLINK_SETUP.md).

## Usage

### Import from LRS

```bash
uv run python main.py import-resume lrs
```

### Import from CSV

```bash
uv run python main.py import-resume csv path/to/file.csv
```

### Import from Cake

```bash
uv run python main.py import-resume cake
```

### Import from Yourator

```bash
uv run python main.py import-resume yourator --file-path ./yourator.xlsx
```

### View Imported Data

```bash
uv run python main.py show-data
```

### Validate Data (without importing)

```bash
uv run python main.py validate-data
```

## Backup Feature

Every time you import resumes, the system automatically backs up resume files to `backup/resume_files/` organized by source. Files are timestamped to avoid conflicts.

## Project Structure

```
import_resume/
├── __init__.py
├── models.py           # Data models (Resume, etc.)
├── interface.py        # Abstract importer interface
├── factory.py          # Importer factory
├── database.py         # Database operations (with backup)
└── drivers/            # Specific importers
    ├── lrs.py
    ├── cake.py
    ├── csv_importer.py
    └── yourator.py
```

## Configuration

### Database Path

Default database path is `resume.db`. You can specify a different path:

```bash
uv run python main.py import-resume lrs --db-path custom.db
```

### Backup Directory

Default backup directory is `backup/resume_files/`. This can be configured when creating the `ResumeDatabase` instance.

## Development

### Run Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run ruff format .
uv run ruff check --fix .
```

## License

[Your License Here]

