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
        """Extract attachments and download only PDF files"""
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
                        
                        # Decode file data
                        file_data = base64.urlsafe_b64decode(attachment['data'])
                        
                        # Check if this is a PDF file
                        mime_type = part.get('mimeType', 'unknown').lower()
                        is_pdf = self._is_pdf_content(file_data, filename, mime_type)
                        
                        if is_pdf:
                            # Create unique filename
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
                            if not safe_filename.lower().endswith('.pdf'):
                                safe_filename += '.pdf'
                            unique_filename = f"{timestamp}_attachment_{safe_filename}"
                            file_path = os.path.join(self.received_files_dir, unique_filename)
                            
                            # Save PDF file
                            with open(file_path, 'wb') as f:
                                f.write(file_data)
                            
                            print(f"Downloaded PDF attachment: {filename} -> {file_path}")
                            
                            attachments.append({
                                'original_filename': filename,
                                'local_path': os.path.abspath(file_path),
                                'mime_type': mime_type,
                                'size_bytes': len(file_data),
                                'attachment_id': attachment_id,
                                'type': 'pdf_attachment'
                            })
                        else:
                            print(f"Skipping non-PDF attachment: {filename} (MIME: {mime_type})")
                        
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
            # Always try to download from URLs, but only save PDFs
            print(f"Attempting to download from URL: {url}")
            download_info = self._download_and_check_pdf_from_url(url)
            if download_info:
                downloads.append(download_info)
        
        return downloads

    def _is_downloadable_file(self, url: str) -> bool:
        """Check if URL points to a downloadable file"""
        
        # File extensions that we want to download
        downloadable_extensions = [
            '.pdf'
            # , '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            # '.zip', '.rar', '.7z', '.tar', '.gz',
            # '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            # '.mp4', '.avi', '.mov', '.wmv', '.flv',
            # '.mp3', '.wav', '.flac', '.aac',
            # '.txt', '.csv', '.json', '.xml',
            # '.apk', '.exe', '.dmg', '.pkg'
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

    def _is_pdf_content(self, file_data: bytes, filename: str, mime_type: str) -> bool:
        """Check if file content is actually a PDF"""
        
        # Check MIME type
        if 'pdf' in mime_type.lower() or 'application/pdf' in mime_type.lower():
            return True
        
        # Check file extension
        if filename.lower().endswith('.pdf'):
            return True
        
        # Check file magic bytes (PDF files start with %PDF)
        if file_data.startswith(b'%PDF-'):
            return True
        
        return False

    def _download_and_check_pdf_from_url(self, url: str) -> Dict:
        """Download content from URL and only save if it's a PDF"""
        try:
            print(f"Downloading content from: {url}")
            
            # Set proper headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Handle special URL types
            modified_url = self._modify_url_for_direct_download(url)
            
            # Download the content
            response = requests.get(modified_url, headers=headers, allow_redirects=True, timeout=60, stream=True)
            response.raise_for_status()
            
            # Download content to memory first
            content_data = b''
            total_size = 0
            max_size = 100 * 1024 * 1024  # 100MB limit
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content_data += chunk
                    total_size += len(chunk)
                    if total_size > max_size:
                        print(f"File too large (>{max_size} bytes), stopping download")
                        return {
                            'url': url,
                            'local_path': None,
                            'error': 'File too large (>100MB)'
                        }
            
            if total_size == 0:
                return {
                    'url': url,
                    'local_path': None,
                    'error': 'Downloaded content is empty'
                }
            
            # Get filename from URL or headers
            filename = self._get_filename_from_url_or_headers(url, response.headers)
            content_type = response.headers.get('content-type', '').lower()
            
            # Check if the downloaded content is a PDF
            is_pdf = self._is_pdf_content(content_data, filename, content_type)
            
            if is_pdf:
                # Save the PDF file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
                if not safe_filename.lower().endswith('.pdf'):
                    safe_filename += '.pdf'
                unique_filename = f"{timestamp}_url_{safe_filename}"
                file_path = os.path.join(self.received_files_dir, unique_filename)
                
                with open(file_path, 'wb') as f:
                    f.write(content_data)
                
                print(f"Successfully downloaded PDF from URL: {filename} ({total_size} bytes) -> {file_path}")
                
                return {
                    'url': url,
                    'original_filename': filename,
                    'local_path': os.path.abspath(file_path),
                    'mime_type': content_type,
                    'size_bytes': total_size,
                    'type': 'pdf_url'
                }
            else:
                print(f"Skipping non-PDF content from URL: {url} (Content-Type: {content_type})")
                return {
                    'url': url,
                    'local_path': None,
                    'error': f'Not a PDF file (Content-Type: {content_type})'
                }
            
        except requests.exceptions.RequestException as e:
            print(f"Network error downloading {url}: {str(e)}")
            return {
                'url': url,
                'local_path': None,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            print(f"Error downloading from {url}: {str(e)}")
            return {
                'url': url,
                'local_path': None,
                'error': str(e)
            }

    def _modify_url_for_direct_download(self, url: str) -> str:
        """Modify URLs to get direct download links"""
        
        # Handle GitHub URLs
        if 'github.com' in url and '/blob/' in url:
            raw_url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
            print(f"Converting GitHub URL to raw: {raw_url}")
            return raw_url
        
        # Handle Google Drive URLs
        if 'drive.google.com' in url:
            if '/file/d/' in url and '/view' in url:
                file_id = url.split('/file/d/')[1].split('/')[0]
                direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                print(f"Converting Google Drive URL to direct download: {direct_url}")
                return direct_url
        
        # Handle Dropbox URLs
        if 'dropbox.com' in url and '?dl=0' in url:
            direct_url = url.replace('?dl=0', '?dl=1')
            print(f"Converting Dropbox URL to direct download: {direct_url}")
            return direct_url
        
        return url

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

    def _is_order_email(self, headers: Dict, body_data: Dict) -> bool:
        """Determine if an email is order-related using intelligent keyword analysis"""
        
        # Combine subject and body for analysis
        subject = headers.get('Subject', '').lower()
        sender = headers.get('From', '').lower()
        body_text = body_data['text'].lower()
        body_html = body_data['html'].lower()
        
        all_content = f"{subject} {body_text} {body_html}".lower()
        
        # Strong order indicators
        strong_order_keywords = [
            'order confirmation', 'purchase confirmation', 'order receipt', 
            'invoice', 'receipt', 'payment confirmation', 'order number',
            'tracking number', 'shipped', 'delivery confirmation',
            'purchase order', 'order details', 'transaction', 'billing',
            'checkout', 'payment successful', 'order complete'
        ]
        
        # Medium order indicators
        medium_order_keywords = [
            'order', 'purchase', 'payment', 'billing', 'invoice',
            'receipt', 'transaction', 'confirmation', 'delivery',
            'shipping', 'tracking', 'paid', 'bought', 'sale'
        ]
        
        # Sender patterns that indicate orders
        order_sender_patterns = [
            'noreply', 'no-reply', 'orders', 'billing', 'payments',
            'invoices', 'receipts', 'confirmation', 'shop', 'store',
            'amazon', 'flipkart', 'myntra', 'meesho', 'zomato',
            'swiggy', 'uber', 'ola', 'paytm', 'razorpay'
        ]
        
        # Check for strong indicators
        strong_matches = sum(1 for keyword in strong_order_keywords if keyword in all_content)
        if strong_matches >= 1:
            print(f"✅ Strong order indicators found: {strong_matches}")
            return True
        
        # Check for medium indicators + sender patterns
        medium_matches = sum(1 for keyword in medium_order_keywords if keyword in all_content)
        sender_matches = sum(1 for pattern in order_sender_patterns if pattern in sender)
        
        if medium_matches >= 2 and sender_matches >= 1:
            print(f"✅ Medium order indicators + sender pattern found")
            return True
        
        if medium_matches >= 3:
            print(f"✅ Multiple order indicators found: {medium_matches}")
            return True
        
        # Check for PDF attachments + order keywords
        if 'pdf' in all_content and medium_matches >= 1:
            print(f"✅ PDF mentioned with order keywords")
            return True
        
        print(f"❌ Not identified as order email (medium: {medium_matches}, sender: {sender_matches})")
        return False

    def get_order_pdf_paths(self, start_time: datetime, end_time: datetime) -> List[str]:
        """
        Get list of PDF file paths from order emails in the specified time range
        
        Args:
            start_time: Start datetime with minute precision
            end_time: End datetime with minute precision
            
        Returns:
            List of absolute file paths to downloaded PDF files
        """
        emails = self.get_emails_by_time_range(start_time, end_time)
        pdf_paths = []
        
        print(f"\n=== Processing {len(emails)} order emails ===")
        
        for email in emails:
            # Collect PDF paths from attachments
            for attachment in email.get('attachments', []):
                if attachment.get('local_path') and attachment.get('type') == 'pdf_attachment':
                    pdf_paths.append(attachment['local_path'])
                    print(f"📎 PDF Attachment: {attachment['original_filename']}")
            
            # Collect PDF paths from URL downloads
            for download in email.get('url_downloads', []):
                if download.get('local_path') and download.get('type') == 'pdf_url':
                    pdf_paths.append(download['local_path'])
                    print(f"🔗 PDF URL: {download['original_filename']}")
        
        print(f"\n📋 Total PDF files found: {len(pdf_paths)}")
        return pdf_paths

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



def get_email_json(start , end ) -> List[Dict]:
    """
    Convert email data to clean JSON format
    
    Args:
        emails: List of email dictionaries from get_emails_by_time_range
        
    Returns:
        List of clean email JSON objects with format:
        {
            "from": "sender@example.com",
            "to": "recipient@example.com", 
            "subject": "Email Subject",
            "date_time": "Thu, 25 Sep 2025 23:13:45 +0530",
            "content": "Full email text content",
            "attachments": ["/path/to/pdf1.pdf", "/path/to/pdf2.pdf"]
        }
    """
    extractor = GmailExtractor()
    emails = extractor.get_emails_by_time_range(start, end)
    extractor.verify_downloaded_files()

    clean_emails = []
    
    for email in emails:
        # Extract PDF file paths from attachments and URL downloads
        pdf_paths = []
        
        # Get PDF attachments
        for attachment in email.get('attachments', []):
            if (attachment.get('local_path') and 
                attachment.get('type') == 'pdf_attachment'):
                pdf_paths.append(attachment['local_path'])
        
        # Get PDF downloads from URLs
        for download in email.get('url_downloads', []):
            if (download.get('local_path') and 
                download.get('type') == 'pdf_url'):
                pdf_paths.append(download['local_path'])
        
        # Create clean email object
        clean_email = {
            "from": email.get('from', 'Unknown'),
            "to": email.get('to', 'Unknown'),
            "subject": email.get('subject', 'No Subject'),
            "date_time": email.get('date', 'Unknown Date'),
            "content": email.get('body_text', '').strip(),
            "attachments": pdf_paths
        }
        
        clean_emails.append(clean_email)
    
    return clean_emails





# ------------------------------_Agent reading emails ---------------------------------------



from phi.agent import Agent
from phi.model.ollama import Ollama
import json

# 1. Agent to understand user travel needs
order_email_detector = Agent(
    model=Ollama(id="llama3.2:latest"),
    name="order_email_detector",
    description="""You MUST return ONLY a Python list. NO explanations, NO code blocks, NO additional text.

TASK: Analyze emails and return PDF paths from order-related emails.

ORDER INDICATORS:
- "order", "purchase", "invoice", "receipt", "payment", "confirmation", "shipped", "delivery", "tracking", "billing"

RESPONSE FORMAT - RETURN EXACTLY ONE OF THESE:

If order emails found:
["/path/to/file1.pdf", "/path/to/file2.pdf"]

If no order emails:
[]

CRITICAL RULES:
1. Return ONLY the list - nothing else
2. NO code blocks, NO explanations, NO extra text
3. Look for order keywords in subject/content
4. Include attachment paths ONLY from order emails
5. Personal emails (resumes, etc.) = ignore completely""",
    # show_tool_calls=True,
)


def get_order_pdf_files(start, end) -> List[str]:
    # start = datetime(2025, 9, 25, 12, 0)  # Dec 1, 2024, 9:00 AM
    # end = datetime(2025, 9, 26, 23, 0)   # Dec 1, 2024, 5:00 PM
        
    emails_json = get_email_json(start, end)
    emails_json_string = json.dumps(emails_json, indent=2)
    order_pdf_files = order_email_detector.print_response(emails_json_string)
    return order_pdf_files

# --------------------------------------------------------------------------------------------

def main():
    print("Order Email PDF Extractor")
    
    
    start = datetime(2025, 9, 25, 12, 0)  # sep 25, 2025, 12:00 PM
    end   = datetime(2025, 9, 26, 23, 0)  # sep 26 , 2025, 23:00 PM
    
    print(get_order_pdf_files(start, end))
   

if __name__ == "__main__":
    main()