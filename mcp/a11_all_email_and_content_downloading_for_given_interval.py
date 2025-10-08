import os
import pickle
import base64
import re
from datetime import datetime
from typing import List, Dict
import mimetypes
import requests
from urllib.parse import urlparse

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
        
        # Extract and download files from URLs in email content
        url_downloads = self._extract_and_download_urls(body_data)
        
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
            'attachments': attachments,
            'url_downloads': url_downloads
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

    def _extract_and_download_urls(self, body_data) -> List[Dict]:
        """Extract URLs from email content and download files"""
        downloads = []
        
        # Combine text and HTML content
        all_content = body_data['text'] + ' ' + body_data['html']
        
        # Find all URLs
        url_patterns = [
            r'https?://[^\s<>"\'`|]+',
            r'www\.[^\s<>"\'`|]+'
        ]
        
        urls = []
        for pattern in url_patterns:
            found_urls = re.findall(pattern, all_content, re.IGNORECASE)
            urls.extend(found_urls)
        
        # Remove duplicates
        urls = list(set(urls))
        
        print(f"Found {len(urls)} URLs in email content")
        
        for url in urls:
            # Check if URL looks like a file
            if self._is_downloadable_file(url):
                download_info = self._download_file_from_url(url)
                if download_info:
                    downloads.append(download_info)
        
        return downloads

    def _is_downloadable_file(self, url: str) -> bool:
        """Check if URL points to a downloadable file"""
        
        # File extensions that we want to download
        downloadable_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.7z', '.tar', '.gz',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            '.mp4', '.avi', '.mov', '.wmv', '.flv',
            '.mp3', '.wav', '.flac', '.aac',
            '.txt', '.csv', '.json', '.xml',
            '.apk', '.exe', '.dmg', '.pkg'
        ]
        
        # Check file extension
        parsed_url = urlparse(url.lower())
        path = parsed_url.path
        
        for ext in downloadable_extensions:
            if path.endswith(ext):
                return True
        
        # Also check for common file hosting patterns
        file_hosting_patterns = [
            'github.com',
            'drive.google.com',
            'dropbox.com',
            'onedrive',
            'amazonaws.com',
            'cloudfront.net',
            'download',
            'attachment',
            'file'
        ]
        
        for pattern in file_hosting_patterns:
            if pattern in url.lower():
                return True
        
        return False

    def _download_file_from_url(self, url: str) -> Dict:
        """Download file from URL with proper headers and error handling"""
        try:
            print(f"Downloading file from: {url}")
            
            # Set proper headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Handle GitHub URLs specially
            if 'github.com' in url and '/blob/' in url:
                # Convert GitHub blob URL to raw URL
                raw_url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
                print(f"Converting GitHub URL to raw: {raw_url}")
                url = raw_url
            
            # Send HEAD request first to get file info
            try:
                head_response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            except:
                # If HEAD fails, skip it and go straight to GET
                head_response = None
            
            # Get filename from URL or Content-Disposition header
            filename = self._get_filename_from_url_or_headers(url, head_response.headers if head_response else {})
            
            # Check file size (limit to 100MB)
            if head_response:
                content_length = head_response.headers.get('content-length')
                if content_length and int(content_length) > 100 * 1024 * 1024:  # 100MB
                    print(f"File too large ({content_length} bytes), skipping: {filename}")
                    return {
                        'url': url,
                        'filename': filename,
                        'local_path': None,
                        'error': 'File too large (>100MB)'
                    }
            
            # Download the file with streaming for large files
            print(f"Starting download of: {filename}")
            response = requests.get(url, headers=headers, allow_redirects=True, timeout=60, stream=True)
            response.raise_for_status()
            
            # Verify we got actual content
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type and response.headers.get('content-length', '0') == '0':
                return {
                    'url': url,
                    'filename': filename,
                    'local_path': None,
                    'error': 'URL returned HTML page instead of file'
                }
            
            # Create unique filename with proper extension
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Ensure filename has proper extension
            if '.' not in filename:
                # Try to guess extension from content-type
                if 'pdf' in content_type:
                    filename += '.pdf'
                elif 'image' in content_type:
                    filename += '.jpg'
                elif 'text' in content_type:
                    filename += '.txt'
            
            safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
            unique_filename = f"{timestamp}_url_{safe_filename}"
            file_path = os.path.join(self.received_files_dir, unique_filename)
            
            # Save file with streaming to handle large files
            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        total_size += len(chunk)
            
            # Verify file was written and has content
            if total_size == 0:
                os.remove(file_path)
                return {
                    'url': url,
                    'filename': filename,
                    'local_path': None,
                    'error': 'Downloaded file is empty'
                }
            
            print(f"Successfully downloaded: {filename} ({total_size} bytes) -> {file_path}")
            
            return {
                'url': url,
                'original_filename': filename,
                'local_path': os.path.abspath(file_path),
                'mime_type': response.headers.get('content-type', 'unknown'),
                'size_bytes': total_size
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Network error downloading {url}: {str(e)}")
            return {
                'url': url,
                'filename': self._get_filename_from_url_or_headers(url, {}),
                'local_path': None,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            print(f"Error downloading file from {url}: {str(e)}")
            return {
                'url': url,
                'filename': self._get_filename_from_url_or_headers(url, {}),
                'local_path': None,
                'error': str(e)
            }

    def _get_filename_from_url_or_headers(self, url: str, headers: dict) -> str:
        """Extract filename from URL or HTTP headers"""
        
        # Try to get filename from Content-Disposition header
        content_disposition = headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"\'')
            return filename
        
        # Extract from URL path
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        if path and '/' in path:
            filename = path.split('/')[-1]
            if filename and '.' in filename:
                return filename
        
        # Default filename
        return f"downloaded_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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

    def verify_downloaded_files(self) -> None:
        """Verify all downloaded files in received_files directory"""
        print(f"\n=== Verifying files in {self.received_files_dir} ===")
        
        if not os.path.exists(self.received_files_dir):
            print("No received_files directory found")
            return
        
        files = os.listdir(self.received_files_dir)
        if not files:
            print("No files found in received_files directory")
            return
        
        print(f"Found {len(files)} files:")
        
        for filename in sorted(files):
            file_path = os.path.join(self.received_files_dir, filename)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                
                # Try to detect file type
                try:
                    import magic
                    file_type = magic.from_file(file_path)
                except:
                    # Fallback to extension-based detection
                    ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                    file_type = f"File extension: .{ext}"
                
                print(f"  {filename}")
                print(f"    Size: {size:,} bytes")
                print(f"    Type: {file_type}")
                print(f"    Path: {os.path.abspath(file_path)}")
                
                # Basic file validation
                if size == 0:
                    print(f"    ⚠️  WARNING: File is empty!")
                elif size < 100:
                    print(f"    ⚠️  WARNING: File is very small ({size} bytes)")
                else:
                    print(f"    ✅ File looks good")
                print()


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
    end = datetime(2025, 9, 26, 23, 0)   # Dec 1, 2024, 5:00 PM
    
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
                    print(f"  - Attachment: {att['original_filename']} -> {att['local_path']}")
        
        print(f"URL Downloads: {len(email['url_downloads'])}")
        if email['url_downloads']:
            for download in email['url_downloads']:
                if download.get('local_path'):
                    print(f"  - URL Download: {download['original_filename']} -> {download['local_path']}")
                else:
                    print(f"  - Failed URL: {download['url']} ({download.get('error', 'Unknown error')})")
        
        print(f"Body preview: {email['body_text'][:200]}...")
        print("-" * 50)
    
    # Verify all downloaded files
    print("\n" + "="*50)
    extractor.verify_downloaded_files()


if __name__ == "__main__":
    main()