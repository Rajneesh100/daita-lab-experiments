import os
import pickle
import base64
import re
from datetime import datetime
from typing import List, Dict
import mimetypes

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

class GmailExtractor:
    def __init__(self):
        self.service = self._get_service()
        self.received_files_dir = "received_files"
        os.makedirs(self.received_files_dir, exist_ok=True)

    def _get_service(self):
        creds = None
        if os.path.exists('token.pkl'):
            with open('token.pkl', 'rb') as f:
                creds = pickle.load(f)
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file('cred.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.pkl', 'wb') as f:
                pickle.dump(creds, f)
        return build('gmail', 'v1', credentials=creds)

    def get_emails_by_time_range(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        Extract all emails within a specific time range.
        
        Args:
            start_time: Start datetime with minute precision
            end_time: End datetime with minute precision
            
        Returns:
            List of dictionaries containing email data with full content
        """
        try:
            # Convert datetime to Gmail query format
            start_timestamp = int(start_time.timestamp())
            end_timestamp = int(end_time.timestamp())
            
            query = f"after:{start_timestamp} before:{end_timestamp}"
            
            # Get all messages in time range
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=500
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            print(f"Found {len(messages)} emails in time range")
            
            for i, msg in enumerate(messages):
                print(f"Processing email {i+1}/{len(messages)}")
                
                # Get full email details
                email = self.service.users().messages().get(
                    userId='me', id=msg['id'], format='full'
                ).execute()
                
                email_data = self._extract_email_data(email)
                email_list.append(email_data)
            
            return email_list
            
        except Exception as e:
            print(f"Error getting emails: {str(e)}")
            return []

    def _extract_email_data(self, email) -> Dict:
        """Extract all data from a single email including attachments"""
        
        # Extract headers
        headers = email['payload'].get('headers', [])
        header_dict = {h['name']: h['value'] for h in headers}
        
        # Extract body content
        body_data = self._extract_body_content(email['payload'])
        
        # Extract and download attachments
        attachments = self._extract_and_download_attachments(email)
        
        # Build email data structure
        email_data = {
            'id': email['id'],
            'thread_id': email.get('threadId', ''),
            'labels': email.get('labelIds', []),
            'snippet': email.get('snippet', ''),
            'internal_date': email.get('internalDate', ''),
            'headers': header_dict,
            'subject': header_dict.get('Subject', 'No Subject'),
            'from': header_dict.get('From', 'Unknown'),
            'to': header_dict.get('To', 'Unknown'),
            'date': header_dict.get('Date', 'Unknown'),
            'body_text': body_data['text'],
            'body_html': body_data['html'],
            'attachments': attachments
        }
        
        return email_data

    def _extract_body_content(self, payload) -> Dict:
        """Extract text and HTML content from email payload"""
        text_content = ""
        html_content = ""
        
        def extract_from_part(part):
            nonlocal text_content, html_content
            
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    try:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        text_content += decoded + "\n"
                    except:
                        pass
                        
            elif mime_type == 'text/html':
                data = part.get('body', {}).get('data')
                if data:
                    try:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        html_content += decoded + "\n"
                    except:
                        pass
            
            # Recursively process parts
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_from_part(subpart)
        
        extract_from_part(payload)
        
        return {
            'text': text_content.strip(),
            'html': html_content.strip()
        }

    def _extract_and_download_attachments(self, email) -> List[Dict]:
        """Extract attachments and download them to received_files directory"""
        attachments = []
        
        def process_part(part, email_id):
            filename = part.get('filename', '')
            
            if filename:
                # Get attachment data
                attachment_id = part.get('body', {}).get('attachmentId')
                if attachment_id:
                    try:
                        # Download attachment
                        attachment = self.service.users().messages().attachments().get(
                            userId='me', messageId=email_id, id=attachment_id
                        ).execute()
                        
                        # Decode and save file
                        file_data = base64.urlsafe_b64decode(attachment['data'])
                        
                        # Create unique filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
                        unique_filename = f"{timestamp}_{safe_filename}"
                        file_path = os.path.join(self.received_files_dir, unique_filename)
                        
                        # Save file
                        with open(file_path, 'wb') as f:
                            f.write(file_data)
                        
                        print(f"Downloaded: {filename} -> {file_path}")
                        
                        # Get file info
                        mime_type = part.get('mimeType', 'unknown')
                        size = len(file_data)
                        
                        attachments.append({
                            'original_filename': filename,
                            'local_path': os.path.abspath(file_path),
                            'mime_type': mime_type,
                            'size_bytes': size,
                            'attachment_id': attachment_id
                        })
                        
                    except Exception as e:
                        print(f"Error downloading attachment {filename}: {str(e)}")
                        attachments.append({
                            'original_filename': filename,
                            'local_path': None,
                            'error': str(e)
                        })
            
            # Process nested parts
            if 'parts' in part:
                for subpart in part['parts']:
                    process_part(subpart, email_id)
        
        process_part(email['payload'], email['id'])
        return attachments

    def get_emails_simple(self, hours_back: int = 24) -> List[Dict]:
        """
        Simple method to get emails from last N hours
        
        Args:
            hours_back: Number of hours to look back from now
            
        Returns:
            List of email dictionaries
        """
        from datetime import timedelta
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        return self.get_emails_by_time_range(start_time, end_time)


# Example usage
def main():
    print("Gmail Extractor - Simple Email Retrieval")
    
    extractor = GmailExtractor()
    
    # Example 1: Get emails from last 24 hours
    # print("\n=== Getting emails from last 24 hours ===")
    # emails = extractor.get_emails_simple(24)
    
    # print(f"\nFound {len(emails)} emails")
    



    # Example 2: Get emails for specific time range
    print("\n=== Getting emails for specific time range ===")
    start = datetime(2025, 9, 25, 22, 0)  # Dec 1, 2024, 9:00 AM
    end = datetime(2025, 9, 25, 23, 0)   # Dec 1, 2024, 5:00 PM
    
    emails = extractor.get_emails_by_time_range(start, end)
    print(f"Found {len(emails)} emails in specified range")
    for i, email in enumerate(emails):  
        print(f"\nEmail {i+1}:")
        print(f"Subject: {email['subject']}")
        print(f"From: {email['from']}")
        print(f"Date: {email['date']}")
        print(f"Attachments: {len(email['attachments'])}")
        if email['attachments']:
            for att in email['attachments']:
                if att.get('local_path'):
                    print(f"  - {att['original_filename']} -> {att['local_path']}")
        print(f"Body preview: {email['body_text']}...")
        print("-" * 50)
    


if __name__ == "__main__":
    main()