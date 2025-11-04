from pathlib import Path

import typer

from import_resume import (
    CakeImporter,
    CSVImporter,
    ImporterFactory,
    LRSImporter,
)
from import_resume.database import ResumeDatabase

app = typer.Typer()

# Create a command group for import-resume commands
import_app = typer.Typer()
app.add_typer(
    import_app, name="import-resume", help="Import resume data from various sources"
)

# Register available importers
ImporterFactory.register("lrs", LRSImporter)
ImporterFactory.register("csv", CSVImporter)
ImporterFactory.register("cake", CakeImporter)


@app.command()
def hello(name: str = typer.Argument("World", help="Name to greet")):
    """
    A simple greeting command.
    """
    typer.echo(f"Hello {name}!")


@import_app.command("lrs")
def import_lrs(
    db_path: str = typer.Option("resume.db", help="Path to SQLite database file"),
    skip_validation: bool = typer.Option(False, help="Skip data validation"),
):
    """
    Import resume data from LRS Google Sheets source.
    """
    try:
        # Create importer and database
        importer = ImporterFactory.create("lrs")
        database = ResumeDatabase(db_path)

        typer.echo(f"Importing data from {importer.source_name}...")

        # Import data
        result = importer.import_data(skip_validation=skip_validation)

        if not result.success:
            typer.echo(f"❌ {result.message}", err=True)
            raise typer.Exit(1)

        # Display validation results
        if result.validation_errors:
            typer.echo(f"⚠️  Found {len(result.validation_errors)} validation errors:")
            for error in result.validation_errors[:10]:  # Show first 10 errors
                typer.echo(f"  Row {error.row_index}: {error.field} - {error.error}")

            if len(result.validation_errors) > 10:
                typer.echo(
                    f"  ... and {len(result.validation_errors) - 10} more errors"
                )

            if not skip_validation and not typer.confirm(
                "Continue with import despite validation errors?"
            ):
                typer.echo("Import cancelled.")
                raise typer.Exit(0)

        typer.echo(
            f"✅ Validated {len(result.valid_resumes)} valid records out of {result.total_records} total records"
        )

        if not result.valid_resumes:
            typer.echo("❌ No valid records to import")
            raise typer.Exit(1)

        # Save to database
        saved_count = database.save_resumes(result.valid_resumes)

        typer.echo(
            f"✅ Successfully imported {saved_count} records from {importer.source_name}"
        )
        typer.echo(f"Database saved to: {Path(db_path).absolute()}")

    except Exception as e:
        typer.echo(f"❌ Error importing from LRS: {e}", err=True)
        raise typer.Exit(1)


@import_app.command("csv")
def import_csv(
    file_path: str = typer.Argument(..., help="Path to CSV file"),
    db_path: str = typer.Option("resume.db", help="Path to SQLite database file"),
    skip_validation: bool = typer.Option(False, help="Skip data validation"),
):
    """
    Import resume data from a local CSV file.
    """
    try:
        csv_file = Path(file_path)
        if not csv_file.exists():
            typer.echo(f"❌ CSV file not found: {csv_file}", err=True)
            raise typer.Exit(1)

        # Create importer and database
        importer = ImporterFactory.create("csv")
        database = ResumeDatabase(db_path)

        typer.echo(f"Importing data from CSV file: {csv_file}")

        # Import data
        result = importer.import_data(
            skip_validation=skip_validation, file_path=str(csv_file)
        )

        if not result.success:
            typer.echo(f"❌ {result.message}", err=True)
            raise typer.Exit(1)

        # Display validation results
        if result.validation_errors:
            typer.echo(f"⚠️  Found {len(result.validation_errors)} validation errors:")
            for error in result.validation_errors[:10]:  # Show first 10 errors
                typer.echo(f"  Row {error.row_index}: {error.field} - {error.error}")

            if len(result.validation_errors) > 10:
                typer.echo(
                    f"  ... and {len(result.validation_errors) - 10} more errors"
                )

            if not skip_validation and not typer.confirm(
                "Continue with import despite validation errors?"
            ):
                typer.echo("Import cancelled.")
                raise typer.Exit(0)

        typer.echo(
            f"✅ Validated {len(result.valid_resumes)} valid records out of {result.total_records} total records"
        )

        if not result.valid_resumes:
            typer.echo("❌ No valid records to import")
            raise typer.Exit(1)

        # Save to database
        saved_count = database.save_resumes(result.valid_resumes)

        typer.echo(f"✅ Successfully imported {saved_count} records from CSV")
        typer.echo(f"Database saved to: {Path(db_path).absolute()}")

    except Exception as e:
        typer.echo(f"❌ Error importing CSV data: {e}", err=True)
        raise typer.Exit(1)


@import_app.command("cake")
def import_cake(
    db_path: str = typer.Option("resume.db", help="Path to SQLite database file"),
    skip_validation: bool = typer.Option(False, help="Skip data validation"),
):
    """
    Import resume data from Cake Google Sheets source.
    """
    try:
        # Create importer and database
        importer = ImporterFactory.create("cake")
        database = ResumeDatabase(db_path)

        typer.echo(f"Importing data from {importer.source_name}...")

        # Import data
        result = importer.import_data(skip_validation=skip_validation)

        if not result.success:
            typer.echo(f"❌ {result.message}", err=True)
            raise typer.Exit(1)

        # Display validation results
        if result.validation_errors:
            typer.echo(f"⚠️  Found {len(result.validation_errors)} validation errors:")
            for error in result.validation_errors[:10]:  # Show first 10 errors
                typer.echo(f"  Row {error.row_index}: {error.field} - {error.error}")

            if len(result.validation_errors) > 10:
                typer.echo(
                    f"  ... and {len(result.validation_errors) - 10} more errors"
                )

            if not skip_validation and not typer.confirm(
                "Continue with import despite validation errors?"
            ):
                typer.echo("Import cancelled.")
                raise typer.Exit(0)

        typer.echo(
            f"✅ Validated {len(result.valid_resumes)} valid records out of {result.total_records} total records"
        )

        if not result.valid_resumes:
            typer.echo("❌ No valid records to import")
            raise typer.Exit(1)

        # Save to database
        saved_count = database.save_resumes(result.valid_resumes)

        typer.echo(
            f"✅ Successfully imported {saved_count} records from {importer.source_name}"
        )
        typer.echo(f"Database saved to: {Path(db_path).absolute()}")

    except Exception as e:
        typer.echo(f"❌ Error importing from Cake: {e}", err=True)
        raise typer.Exit(1)


@import_app.command("hr")
def import_hr(
    db_path: str = typer.Option("resume.db", help="Path to SQLite database file"),
    skip_validation: bool = typer.Option(False, help="Skip data validation"),
):
    """
    Import resume data from HR department source (placeholder for future implementation).
    """
    available_sources = ImporterFactory.get_available_sources()
    typer.echo("❌ HR import source not yet implemented")
    typer.echo(f"Available sources: {', '.join(available_sources)}")
    raise typer.Exit(1)


@import_app.command("linkedin")
def import_linkedin(
    db_path: str = typer.Option("resume.db", help="Path to SQLite database file"),
    skip_validation: bool = typer.Option(False, help="Skip data validation"),
):
    """
    Import resume data from LinkedIn source (placeholder for future implementation).
    """
    available_sources = ImporterFactory.get_available_sources()
    typer.echo("❌ LinkedIn import source not yet implemented")
    typer.echo(f"Available sources: {', '.join(available_sources)}")
    raise typer.Exit(1)


@app.command()
def validate_data():
    """
    Validate resume data from LRS Google Sheets without importing.
    """
    try:
        # Create LRS importer
        importer = ImporterFactory.create("lrs")

        typer.echo(f"Validating data from {importer.source_name}...")

        # Import data with validation (but don't save)
        result = importer.import_data(skip_validation=False)

        typer.echo("\n📊 Validation Summary:")
        typer.echo(f"  Total records: {result.total_records}")
        typer.echo(f"  Valid records: {len(result.valid_resumes)}")
        typer.echo(
            f"  Invalid records: {result.total_records - len(result.valid_resumes)}"
        )
        typer.echo(f"  Validation errors: {len(result.validation_errors)}")

        if result.validation_errors:
            typer.echo("\n❌ Validation Errors:")
            for error in result.validation_errors:
                typer.echo(f"  Row {error.row_index}: {error.field} - {error.error}")
        else:
            typer.echo("\n✅ All data is valid!")

    except Exception as e:
        typer.echo(f"❌ Error validating data: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def show_data(
    db_path: str = typer.Option("resume.db", help="Path to SQLite database file"),
    limit: int = typer.Option(10, help="Number of rows to display"),
    source: str = typer.Option(None, help="Filter by source (lrs, csv, etc.)"),
):
    """
    Display resume data from the SQLite database.
    """
    try:
        database = ResumeDatabase(db_path)

        if not database.database_exists():
            typer.echo(f"❌ Database file not found: {db_path}", err=True)
            raise typer.Exit(1)

        resumes = database.get_resumes(limit=limit, source=source)

        if not resumes:
            filter_msg = f" (filtered by source: {source})" if source else ""
            typer.echo(f"No resume records found in the database{filter_msg}.")
            return

        total_count = database.count_resumes(source=source)
        filter_msg = f" (filtered by source: {source})" if source else ""

        typer.echo(
            f"Showing first {len(resumes)} of {total_count} resume records{filter_msg}:"
        )
        typer.echo("-" * 80)

        for i, resume in enumerate(resumes, 1):
            typer.echo(f"Record {i}:")
            typer.echo(f"  ID: {resume.id}")
            typer.echo(f"  Name: {resume.full_name}")
            typer.echo(f"  Email: {resume.email}")
            typer.echo(f"  Phone: {resume.phone}")
            typer.echo(f"  Resume File: {resume.resume_file}")
            typer.echo(f"  Position Applied: {resume.position_applied}")
            typer.echo(f"  Test Score: {resume.test_score}")
            typer.echo(f"  Interview Status: {resume.interview_status}")
            typer.echo(f"  Application Status: {resume.application_status}")
            typer.echo(f"  Source: {resume.source}")
            typer.echo(f"  Created: {resume.created_at}")
            if resume.recruiter_notes:
                typer.echo(f"  Recruiter Notes: {resume.recruiter_notes}")
            if resume.hr_notes:
                typer.echo(f"  HR Notes: {resume.hr_notes}")
            typer.echo("-" * 80)

    except Exception as e:
        typer.echo(f"❌ Error reading data: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
