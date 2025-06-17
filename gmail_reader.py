from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import os.path
from datetime import datetime, timedelta
import base64
from email.mime.text import MIMEText
import re

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Gets an authorized Gmail API service instance."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def search_emails(service, query='', start_date=None, end_date=None):
    """
    Search for emails based on query and date range.
    
    Args:
        service: Gmail API service instance
        query: Search query string (e.g., 'subject:important')
        start_date: Start date in YYYY/MM/DD format
        end_date: End date in YYYY/MM/DD format
    
    Returns:
        List of email messages matching the criteria
    """
    # Build the search query
    search_query = []
    
    if query:
        search_query.append(query)
    
    if start_date:
        search_query.append(f'after:{start_date}')
    if end_date:
        search_query.append(f'before:{end_date}')
    
    # Combine all search criteria
    final_query = ' '.join(search_query)
    
    try:
        # Call the Gmail API to fetch messages
        results = service.users().messages().list(userId='me', q=final_query).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print('No messages found.')
            return []
        
        # Get full message details for each message
        full_messages = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            full_messages.append(msg)
        
        return full_messages
    
    except Exception as e:
        print(f'An error occurred: {e}')
        return []

def get_email_details(message):
    """Extract relevant details from an email message."""
    headers = message['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
    sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
    date = next((header['value'] for header in headers if header['name'] == 'Date'), 'Unknown Date')
    
    # Get email body
    body = ''
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                body = base64.urlsafe_b64decode(part['body']['data']).decode()
                break
    elif 'body' in message['payload'] and 'data' in message['payload']['body']:
        body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode()
    
    return {
        'subject': subject,
        'sender': sender,
        'date': date,
        'body': body
    }

def main():
    # Get Gmail service
    service = get_gmail_service()
    
    # Example usage
    print("Enter search criteria:")
    subject_query = input("Enter subject to search (press Enter to skip): ")
    start_date = input("Enter start date (YYYY/MM/DD) or press Enter to skip: ")
    end_date = input("Enter end date (YYYY/MM/DD) or press Enter to skip: ")
    
    # Build search query
    query = f'subject:{subject_query}' if subject_query else ''
    
    # Search for emails
    messages = search_emails(service, query, start_date, end_date)
    
    # Display results
    print(f"\nFound {len(messages)} messages:")
    for message in messages:
        details = get_email_details(message)
        print("\n" + "="*50)
        print(f"Subject: {details['subject']}")
        print(f"From: {details['sender']}")
        print(f"Date: {details['date']}")
        print(f"Body: {details['body'][:200]}...")  # Show first 200 characters of body

if __name__ == '__main__':
    main() 