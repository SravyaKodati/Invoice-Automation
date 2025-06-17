import pandas as pd
import re
from datetime import datetime
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
            df = pd.DataFrame(columns=['email_id', 'invoice_number', 'due_date', 'budget', 'extraction_date'])
            df.to_csv(self.output_file, index=False)

    def extract_invoice_details(self, email_body):
        """Extract invoice details using regex patterns."""
        patterns = {
            'invoice_number': r'(?i)invoice\s*(?:number|#|no)?[:#]?\s*([A-Z0-9-]+)',
            'due_date': r'(?i)due\s*date[:#]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            'budget': r'(?i)(?:budget|amount|total)[:#]?\s*[$€£]?\s*([\d,]+\.?\d*)'
        }
        
        extracted_data = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, email_body)
            extracted_data[field] = match.group(1) if match else None
        
        return extracted_data

    def validate_with_llm(self, email_body, field, current_value):
        """Use LLM to validate and extract missing values."""
        prompt = f"""
        Analyze the following email body and extract the {field} if present. 
        If the value is clearly missing (not just written differently), respond with 'MISSING_VALUE'.
        If you find the value, provide it in a clear format.
        
        Email body:
        {email_body}
        
        Current extracted value: {current_value}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise data extraction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            return result if result != 'MISSING_VALUE' else None
            
        except Exception as e:
            logger.error(f"Error in LLM validation: {e}")
            return None

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
            
            # Extract email body
            body = ''
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(part['body']['data']).decode()
                        break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode()
            
            # Extract invoice details
            extracted_data = self.extract_invoice_details(body)
            
            # Validate missing values with LLM
            for field, value in extracted_data.items():
                if value is None:
                    llm_value = self.validate_with_llm(body, field, value)
                    if llm_value:
                        extracted_data[field] = llm_value
            
            # Create new record
            new_record = {
                'email_id': message['id'],
                'invoice_number': extracted_data['invoice_number'],
                'due_date': extracted_data['due_date'],
                'budget': extracted_data['budget'],
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