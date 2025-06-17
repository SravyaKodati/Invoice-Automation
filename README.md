# Gmail Reader

This script allows you to read and filter emails from your Gmail account based on subject lines and date ranges.

## Setup Instructions

1. First, install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up Google Cloud Project and enable Gmail API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project
   - Go to the Credentials page
   - Create an OAuth 2.0 Client ID
   - Download the credentials and save them as `credentials.json` in the same directory as the script

3. Run the script:
   ```bash
   python gmail_reader.py
   ```

## Usage

When you run the script for the first time, it will:
1. Open your default web browser
2. Ask you to sign in to your Google account
3. Request permission to access your Gmail
4. Save the authentication token for future use

After authentication, you can:
- Search for emails by subject
- Filter emails by date range
- View email details including sender, subject, date, and body

## Features

- Search emails by subject line
- Filter emails by date range
- View email details (sender, subject, date, body)
- Secure authentication using OAuth 2.0
- Automatic token refresh

## Notes

- The script requires Python 3.6 or higher
- Make sure to keep your `credentials.json` and `token.pickle` files secure
- The script only has read-only access to your Gmail account 