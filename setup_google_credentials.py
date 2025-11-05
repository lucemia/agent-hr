#!/usr/bin/env python3
"""
Helper script to set up Google service account credentials for hyperlink extraction.

This script helps you:
1. Create a service account in Google Cloud Console
2. Download and configure credentials
3. Share the Google Sheet with the service account
4. Test the setup
"""

import json
import os
import sys
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials

    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("⚠️  gspread is not installed. Installing now...")
    print("Run: uv add gspread")
    sys.exit(1)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num: int, description: str):
    """Print a formatted step."""
    print(f"\n📋 Step {step_num}: {description}")


def check_existing_credentials() -> Path | None:
    """Check if credentials already exist."""
    # Check default location
    default_path = Path.home() / ".config" / "gspread" / "service_account.json"
    if default_path.exists():
        return default_path

    # Check environment variable
    env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    return None


def validate_credentials_file(cred_path: Path) -> bool:
    """Validate that the credentials JSON file is valid."""
    try:
        with open(cred_path) as f:
            creds = json.load(f)

        # Check required fields
        required_fields = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
        ]
        for field in required_fields:
            if field not in creds:
                print(f"❌ Credentials file missing required field: {field}")
                return False

        if creds.get("type") != "service_account":
            print("❌ Credentials file is not a service account type")
            return False

        print("✅ Credentials file is valid")
        print(f"   Service Account Email: {creds['client_email']}")
        return True
    except json.JSONDecodeError:
        print("❌ Credentials file is not valid JSON")
        return False
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return False


def test_credentials(cred_path: Path, sheet_id: str) -> bool:
    """Test if credentials can access the Google Sheet."""
    try:
        print("\n🔍 Testing credentials...")
        gc = gspread.service_account(filename=str(cred_path))

        # Try to open the sheet
        sheet = gc.open_by_key(sheet_id)
        print(f"✅ Successfully connected to Google Sheet: {sheet.title}")

        # Try to get worksheet
        worksheet = sheet.get_worksheet_by_id(int("127001815"))  # LRS gid
        print(f"✅ Successfully accessed worksheet: {worksheet.title}")

        return True
    except Exception as e:
        print(f"❌ Failed to access Google Sheet: {e}")
        print(
            "\n💡 Make sure you've shared the Google Sheet with the service account email:"
        )
        print(f"   {json.load(open(cred_path))['client_email']}")
        return False


def setup_credentials():
    """Main setup function."""
    print_section("Google Sheets Credentials Setup")
    print("\nThis script will help you set up Google service account credentials")
    print("to extract hyperlinks from Google Sheets.")

    # Check if credentials already exist
    existing = check_existing_credentials()
    if existing:
        print(f"\n✅ Found existing credentials at: {existing}")
        if validate_credentials_file(existing):
            use_existing = input("\nUse existing credentials? (y/n): ").lower().strip()
            if use_existing == "y":
                # Test existing credentials
                sheet_id = "1mGpl2LzdXZlrKYXatWdAKQrI5SsagjTEen58xtjDNms"
                if test_credentials(existing, sheet_id):
                    print("\n🎉 Setup complete! Your credentials are working.")
                    return
                else:
                    print("\n⚠️  Existing credentials failed. Let's set up new ones.")

    print_section("Setup Instructions")

    print_step(1, "Create Google Cloud Project and Service Account")
    print("""
   1. Go to: https://console.cloud.google.com/
   2. Create a new project or select an existing one
   3. Go to "APIs & Services" > "Library"
   4. Search for "Google Sheets API" and click "Enable"
   5. Go to "APIs & Services" > "Credentials"
   6. Click "Create Credentials" > "Service Account"
   7. Fill in the service account details:
      - Name: "resume-import" (or any name you prefer)
      - Description: "For importing resume data from Google Sheets"
   8. Click "Create and Continue"
   9. Skip role assignment (click "Continue")
  10. Click "Done"
    """)

    input("Press Enter when you've completed Step 1...")

    print_step(2, "Download Service Account Key")
    print("""
   1. In the Credentials page, find your service account
   2. Click on the service account email
   3. Go to the "Keys" tab
   4. Click "Add Key" > "Create new key"
   5. Choose "JSON" format
   6. Click "Create" - the JSON file will download automatically
    """)

    json_path = input("\nEnter the path to the downloaded JSON file: ").strip()
    json_path = Path(json_path).expanduser().resolve()

    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        return

    if not validate_credentials_file(json_path):
        return

    # Load credentials to get email
    with open(json_path) as f:
        creds_data = json.load(f)
    service_account_email = creds_data["client_email"]

    print_step(3, "Install Credentials")
    cred_dir = Path.home() / ".config" / "gspread"
    cred_dir.mkdir(parents=True, exist_ok=True)
    target_path = cred_dir / "service_account.json"

    # Copy credentials file
    import shutil

    shutil.copy2(json_path, target_path)
    print(f"✅ Credentials installed to: {target_path}")

    # Set permissions
    os.chmod(target_path, 0o600)
    print("✅ Set secure permissions on credentials file")

    print_step(4, "Share Google Sheet with Service Account")
    print(f"""
   1. Open your Google Sheet:
      https://docs.google.com/spreadsheets/d/1mGpl2LzdXZlrKYXatWdAKQrI5SsagjTEen58xtjDNms
   
   2. Click the "Share" button (top right)
   
   3. Add this email address:
      {service_account_email}
   
   4. Give it "Viewer" access
   
   5. Uncheck "Notify people" (optional)
   
   6. Click "Share"
    """)

    input("Press Enter when you've shared the sheet with the service account...")

    print_step(5, "Test Setup")
    sheet_id = "1mGpl2LzdXZlrKYXatWdAKQrI5SsagjTEen58xtjDNms"
    if test_credentials(target_path, sheet_id):
        print_section("✅ Setup Complete!")
        print("\n🎉 Your credentials are configured and working!")
        print("\nYou can now run the import and it will extract URLs from hyperlinks:")
        print("   uv run python main.py import-resume lrs")
    else:
        print_section("⚠️ Setup Incomplete")
        print("\nThe credentials are installed but couldn't access the sheet.")
        print("Please make sure you've:")
        print("  1. Shared the Google Sheet with the service account email")
        print("  2. Enabled Google Sheets API in your Google Cloud project")


def main():
    """Main entry point."""
    if not GSPREAD_AVAILABLE:
        print("❌ gspread is not available. Please install it first:")
        print("   uv add gspread")
        sys.exit(1)

    try:
        setup_credentials()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
