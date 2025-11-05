# Setting Up Google Sheets Hyperlink Extraction

The LRS importer can extract URLs from Google Sheets hyperlinks, but it requires Google service account credentials to be set up.

## Why This Is Needed

Google Sheets CSV export converts hyperlinks to display text (filenames), losing the actual URLs. To preserve the URLs, we need to use the Google Sheets API which requires authentication.

## Setup Instructions

### Option 1: Service Account (Recommended)

1. **Create a Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google Sheets API:**
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

3. **Create a Service Account:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the details and create the account

4. **Create and Download Key:**
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format and download

5. **Share the Google Sheet:**
   - Open your Google Sheet
   - Click "Share" button
   - Add the service account email (found in the JSON file as `client_email`)
   - Give it "Viewer" access

6. **Set Up Credentials:**
   - Place the downloaded JSON file at:
     ```
     ~/.config/gspread/service_account.json
     ```
   - Or set the environment variable:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service_account.json"
     ```

### Option 2: Using Environment Variable

You can also set the credentials path directly:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service_account.json"
```

## Verification

After setting up credentials, run the import again:

```bash
uv run python main.py import-resume lrs
```

The importer will automatically extract URLs from hyperlinks and replace the filenames with actual URLs.

## Troubleshooting

- **"No service account credentials found"**: Make sure the JSON file is in the correct location or the environment variable is set
- **"Permission denied"**: Make sure you've shared the Google Sheet with the service account email
- **"API not enabled"**: Make sure Google Sheets API is enabled in your Google Cloud project

## Notes

- Without credentials, the importer will still work but will only get filenames from CSV export
- The hyperlink extraction is optional and won't break the import if it fails
- Only URLs in the `履歷` (resume_file) column will be extracted

