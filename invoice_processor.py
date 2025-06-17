import pandas as pd
import re
from datetime import datetime, timedelta
import json
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import base64
from openai import OpenAI
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InvoiceProcessor:
    def __init__(self, openai_api_key, credentials_path='credentials.json'):
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.credentials_path = credentials_path
        self.gmail_service = self._get_gmail_service()
        self.output_file = 'invoice_data.csv'
        self._initialize_output_file()

    def _get_gmail_service(self):
        """Initialize Gmail API service."""
        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        creds = None
        
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('gmail', 'v1', credentials=creds)

    def _initialize_output_file(self):
        """Create output file if it doesn't exist."""
        if not os.path.exists(self.output_file):
            df = pd.DataFrame(columns=['email_id', 'invoice_number', 'amount_due', 'due_date', 'extraction_date'])
            df.to_csv(self.output_file, index=False)

    def extract_invoice_details(self, email_body, sent_date):
        """Extract invoice details using regex patterns."""
        info = {
            "invoice_number": None,
            "amount_due": None,
            "due_date": None
        }

        # Invoice number
        match = re.search(r'invoice\s*[#:]*\s*(\d+)', email_body, re.IGNORECASE)
        if match:
            info["invoice_number"] = match.group(1)

        # Amount
        match = re.search(r'\$\s?([\d,]+(?:\.\d{2})?)', email_body)
        if match:
            info["amount_due"] = f"${match.group(1)}"

        # Explicit due date
        match = re.search(r'due (?:by|on|before)?\s*(\w+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?)', email_body, re.IGNORECASE)
        if match:
            try:
                info["due_date"] = str(datetime.strptime(match.group(1).replace(',', ''), "%B %d %Y").date())
            except:
                try:
                    info["due_date"] = str(datetime.strptime(match.group(1), "%B %d").replace(year=sent_date.year).date())
                except:
                    pass

        # Relative terms: Net 15, within 30 days, etc.
        match = re.search(r'(net|within)\s*(\d{1,2})', email_body, re.IGNORECASE)
        if match and sent_date:
            days = int(match.group(2))
            info["due_date"] = str((sent_date + timedelta(days=days)).date())

        return info

    def validate_with_llm(self, email_body, extracted_data):
        """Use LLM to validate and extract missing values in a single API call."""
        prompt = f"""
        Analyze the following email body and extract invoice details. For each field, if the value is clearly missing (not just written differently), respond with 'MISSING_VALUE'.
        If you find the value, provide it in a clear format.
        
        Required fields:
        1. invoice_number: Extract the invoice number
        2. amount_due: Extract the amount due (include $ symbol)
        3. due_date: Extract the due date in YYYY-MM-DD format
        
        Current extracted values:
        {json.dumps(extracted_data, indent=2)}
        
        Email body:
        {email_body}
        
        Provide your response in JSON format with the following structure:
        {{
            "invoice_number": "value or MISSING_VALUE",
            "amount_due": "value or MISSING_VALUE",
            "due_date": "value or MISSING_VALUE"
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise data extraction assistant. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            # Update only missing values
            for field, value in result.items():
                if extracted_data[field] is None and value != "MISSING_VALUE":
                    extracted_data[field] = value
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error in LLM validation: {e}")
            return extracted_data

    def process_emails(self, days_back=7):
        """Process new emails and update the invoice data file."""
        # Read existing data
        df = pd.read_csv(self.output_file)
        processed_emails = set(df['email_id'].tolist())
        
        # Calculate date range
        end_date = datetime.now().strftime('%Y/%m/%d')
        start_date = (datetime.now() - pd.Timedelta(days=days_back)).strftime('%Y/%m/%d')
        
        # Search for new emails
        query = f'after:{start_date} before:{end_date}'
        results = self.gmail_service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        new_records = []
        for message in messages:
            if message['id'] in processed_emails:
                continue
                
            msg = self.gmail_service.users().messages().get(userId='me', id=message['id']).execute()
            
            # Get sent date from email headers
            headers = msg['payload']['headers']
            sent_date_str = next((header['value'] for header in headers if header['name'] == 'Date'), None)
            sent_date = datetime.strptime(sent_date_str, "%a, %d %b %Y %H:%M:%S %z").replace(tzinfo=None) if sent_date_str else datetime.now()
            
            # Extract email body
            body = ''
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(part['body']['data']).decode()
                        break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode()
            
            # Extract invoice details using regex
            extracted_data = self.extract_invoice_details(body, sent_date)
            
            # If any field is missing, use LLM to validate
            if any(value is None for value in extracted_data.values()):
                extracted_data = self.validate_with_llm(body, extracted_data)
            
            # Create new record
            new_record = {
                'email_id': message['id'],
                'invoice_number': extracted_data['invoice_number'],
                'amount_due': extracted_data['amount_due'],
                'due_date': extracted_data['due_date'],
                'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            new_records.append(new_record)
        
        # Update the CSV file
        if new_records:
            new_df = pd.DataFrame(new_records)
            df = pd.concat([df, new_df], ignore_index=True)
            df.to_csv(self.output_file, index=False)
            logger.info(f"Added {len(new_records)} new records to {self.output_file}")
        else:
            logger.info("No new records to add")

def main():
    # Initialize the processor with your OpenAI API key
    processor = InvoiceProcessor(openai_api_key='your-openai-api-key')
    
    # Process emails from the last 7 days
    processor.process_emails(days_back=7)

if __name__ == '__main__':
    main() 