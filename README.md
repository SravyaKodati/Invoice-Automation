# Invoice Email Processor

This tool helps you automatically extract invoice details from your Gmail emails. It reads your emails, finds invoice information, and saves it to a spreadsheet.

## What This Tool Does

1. Reads your Gmail emails
2. Looks for invoice details like:
   - Invoice numbers
   - Amount due
   - Due dates
3. If it can't find some information, it uses AI to help find it
4. Saves everything to a spreadsheet that you can easily check

## Setup Steps

### 1. Install Required Tools
First, install the tools you need by running this command:
```bash
pip install -r requirements.txt
```

### 2. Set Up Gmail Access
You need to give the tool permission to read your emails:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Look for "Gmail API" and turn it on
4. Go to "Credentials"
5. Click "Create Credentials" and choose "OAuth 2.0 Client ID"
6. Download the credentials and save them as `credentials.json` in the same folder as the script

### 3. Get an OpenAI API Key
You'll need this for the AI part that helps find missing information:
1. Go to [OpenAI's website](https://platform.openai.com/)
2. Sign up or log in
3. Go to your account settings
4. Create a new API key
5. Copy the key - you'll need it in the next step

### 4. Update the Script
Open `invoice_processor.py` and find this line near the bottom:
```python
processor = InvoiceProcessor(openai_api_key='your-openai-api-key')
```
Replace 'your-openai-api-key' with the API key you copied.

## How to Use

1. Run the script:
```bash
python invoice_processor.py
```

2. The first time you run it:
   - A browser window will open
   - Sign in to your Google account
   - Click "Allow" to give the tool permission to read your emails
   - The tool will create a `token.pickle` file that saves your permission
   - This means you won't need to sign in again next time

### About token.pickle
- This file is created automatically after your first successful sign-in
- It stores your Google account permission securely
- As long as this file exists, you won't need to sign in again
- If you want to use a different Google account, just delete this file
- The file is created in the same folder as your script

3. The tool will then:
   - Look for new emails from the last 7 days
   - Find invoice information in these emails
   - Save the information to a file called `invoice_data.csv`

## What You'll Get

The tool creates a spreadsheet (`invoice_data.csv`) with these columns:
- `email_id`: A unique number for each email
- `invoice_number`: The invoice number found in the email
- `amount_due`: How much needs to be paid
- `due_date`: When the payment is due
- `extraction_date`: When the tool found this information

## How It Works

1. **Email Reading**:
   - The tool checks your Gmail for new emails
   - It looks at emails from the last 7 days (you can change this)

2. **Information Finding**:
   - First, it looks for information using specific patterns (like "Invoice #123" or "Due by July 1, 2025")
   - If it can't find something, it uses AI to help look for it
   - The AI is smart enough to understand different ways people might write the same information

3. **Saving Information**:
   - All found information goes into a spreadsheet
   - New information gets added to the existing spreadsheet
   - You won't get duplicate entries

## Tips

- The tool only looks at new emails it hasn't seen before
- If you want to look at a different time period, you can change the `days_back` number in the script
- The spreadsheet is easy to open in Excel or Google Sheets
- If you need to start fresh, you can delete the `invoice_data.csv` file
- Keep your `token.pickle` file safe - it's your key to accessing your emails without signing in again

## Troubleshooting

If something goes wrong:
1. Check that your `credentials.json` file is in the right place and permissions are enabled on google cloud
2. Make sure you've put in your OpenAI API key correctly
3. If you get an error about permissions, try deleting the `token.pickle` file and running the script again

## Need Help?

If you run into any problems or have questions, feel free to ask! The tool is designed to be user-friendly, but sometimes things need a little tweaking to work just right for your specific needs (I tried this out in colab initially but ran into permission issues, so switched back to VS code).