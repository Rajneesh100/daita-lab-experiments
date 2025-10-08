import os
import pickle
import base64
import re
from email.mime.text import MIMEText
from typing import Optional

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.python import PythonTools
from phi.tools.googlesearch import GoogleSearch
from phi.tools.crawl4ai_tools import Crawl4aiTools
from phi.tools import Toolkit
from phi.memory.agent import AgentMemory

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

class GmailTools(Toolkit):
    def __init__(self):
        super().__init__(name="gmail_tools")
        self.service = self._get_service()
        self.register(self.read_emails)
        self.register(self.send_email)
        self.register(self.read_recent_emails_simple)
        self.register(self.get_email_details)
        self.register(self.bulk_fetch_emails)
        self.register(self.search_emails_simple)
        self.register(self.search_emails_by_sender)
        self.register(self.search_emails_by_subject)
        self.register(self.extract_email_content)

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

    def read_emails(self) -> str:
        """Fetch unread emails and return detailed information"""
        try:
            results = self.service.users().messages().list(
                userId='me', labelIds=['INBOX'], q='is:unread'
            ).execute()
            messages = results.get('messages', [])
            if not messages:
                return "No unread emails found."
            
            email_details = []
            for msg in messages[:5]:
                email = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                snippet = email.get('snippet', 'No preview available')
                
                email_details.append(f"""
Email {len(email_details) + 1}:
From: {sender}
Subject: {subject}
Date: {date}
Preview: {snippet}
---""")
            
            return f"Found {len(messages)} unread emails. Details:\n" + "\n".join(email_details)
            
        except Exception as e:
            return f"Error reading emails: {str(e)}"

    def read_recent_emails_simple(self) -> str:
        """Fetch recent emails from inbox"""
        try:
            results = self.service.users().messages().list(
                userId='me', labelIds=['INBOX'], maxResults=10
            ).execute()
            messages = results.get('messages', [])
            if not messages:
                return "No emails found in inbox."
            
            email_details = []
            for msg in messages:
                email = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                labels = email.get('labelIds', [])
                status = "UNREAD" if 'UNREAD' in labels else "READ"
                
                snippet = email.get('snippet', 'No preview available')
                
                email_details.append(f"""
Email {len(email_details) + 1} ({status}):
From: {sender}
Subject: {subject}
Date: {date}
Preview: {snippet}
---""")
            
            return f"Recent emails from inbox:\n" + "\n".join(email_details)
            
        except Exception as e:
            return f"Error reading recent emails: {str(e)}"

    def get_email_details(self, email_id: str) -> str:
        """Get full details of a specific email by ID"""
        try:
            email = self.service.users().messages().get(userId='me', id=email_id).execute()
            
            headers = email['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            to = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
            
            body = self._extract_email_body(email['payload'])
            
            return f"""
Email Details:
From: {sender}
To: {to}
Subject: {subject}
Date: {date}
Body: {body}
"""
            
        except Exception as e:
            return f"Error getting email details: {str(e)}"

    def extract_email_content(self, email_id: str) -> str:
        """Extract comprehensive raw content from email for LLM analysis"""
        try:
            email = self.service.users().messages().get(userId='me', id=email_id, format='full').execute()
            
            # Extract all headers
            headers = email['payload'].get('headers', [])
            header_data = {}
            for header in headers:
                header_data[header['name']] = header['value']
            
            # Extract body content (all parts)
            body_content = self._extract_all_content(email['payload'])
            
            # Extract attachments info
            attachments = self._extract_attachment_info(email['payload'])
            
            # Extract links
            links = self._extract_links(body_content['text'] + ' ' + body_content['html'])
            
            # Check for order-related keywords
            full_text = f"{header_data.get('Subject', '')} {body_content['text']}".lower()
            order_keywords = [
                'order', 'purchase', 'receipt', 'invoice', 'payment', 'confirmation',
                'shipped', 'delivery', 'tracking', 'pdf', 'attachment', 'bill',
                'transaction', 'checkout', 'cart', 'buy', 'bought', 'sale'
            ]
            
            order_related = any(keyword in full_text for keyword in order_keywords)
            
            # Format comprehensive output
            result = f"""
EMAIL CONTENT ANALYSIS
======================

BASIC INFO:
ID: {email_id}
Subject: {header_data.get('Subject', 'No Subject')}
From: {header_data.get('From', 'Unknown')}
To: {header_data.get('To', 'Unknown')}
Date: {header_data.get('Date', 'Unknown')}
Message-ID: {header_data.get('Message-ID', 'Unknown')}

STATUS:
Labels: {', '.join(email.get('labelIds', []))}
Thread ID: {email.get('threadId', 'Unknown')}
Internal Date: {email.get('internalDate', 'Unknown')}

CONTENT:
Plain Text:
{body_content['text'][:2000]}{'...' if len(body_content['text']) > 2000 else ''}

HTML Content:
{body_content['html'][:1000]}{'...' if len(body_content['html']) > 1000 else ''}

ATTACHMENTS:
{attachments if attachments else 'No attachments found'}

LINKS FOUND:
{chr(10).join(links[:20]) if links else 'No links found'}

ORDER ANALYSIS:
Order Related: {'Yes' if order_related else 'No'}
Keywords Found: {[kw for kw in order_keywords if kw in full_text]}

PDF LINKS:
{chr(10).join([link for link in links if 'pdf' in link.lower() or 'invoice' in link.lower() or 'receipt' in link.lower()])}

ALL HEADERS:
{chr(10).join([f'{k}: {v}' for k, v in header_data.items()])}
"""
            
            return result
            
        except Exception as e:
            return f"Error extracting email content: {str(e)}"

    def _extract_all_content(self, payload):
        """Extract all text and HTML content from email payload"""
        text_content = ""
        html_content = ""
        
        def extract_from_part(part):
            nonlocal text_content, html_content
            
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    try:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        text_content += decoded + "\n"
                    except:
                        pass
                        
            elif part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data')
                if data:
                    try:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        html_content += decoded + "\n"
                        # Also extract text from HTML
                        text_from_html = re.sub(r'<[^>]+>', '', decoded)
                        text_content += text_from_html + "\n"
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

    def _extract_attachment_info(self, payload):
        """Extract attachment information"""
        attachments = []
        
        def find_attachments(part):
            if part.get('filename'):
                size = part.get('body', {}).get('size', 0)
                attachments.append(f"File: {part['filename']} (Size: {size} bytes)")
            
            if 'parts' in part:
                for subpart in part['parts']:
                    find_attachments(subpart)
        
        find_attachments(payload)
        return attachments

    def _extract_links(self, text):
        """Extract all links from text"""
        if not text:
            return []
        
        # Find URLs
        url_pattern = r'https?://[^\s<>"\'`|]+|www\.[^\s<>"\'`|]+'
        links = re.findall(url_pattern, text, re.IGNORECASE)
        
        return list(set(links))

    def _extract_email_body(self, payload) -> str:
        """Extract email body from payload (basic version)"""
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body[:500] + "..." if len(body) > 500 else body

    def send_email(self, to: str, subject: str, body: str) -> str:
        """Send an email via Gmail"""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.service.users().messages().send(userId='me', body={'raw': raw}).execute()
            return f"Email successfully sent to {to} with subject: '{subject}'"
        except Exception as e:
            return f"Error sending email: {str(e)}"

    def bulk_fetch_emails(self, limit: int = 1000, label: str = "INBOX") -> str:
        """Bulk fetch emails with configurable limit"""
        try:
            if limit > 1000:
                limit = 1000
                print("Limit capped at 1000 emails for performance")
            
            results = self.service.users().messages().list(
                userId='me', labelIds=[label], maxResults=limit
            ).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return f"No emails found in {label}."
            
            email_summaries = []
            print(f"Fetching {len(messages)} emails...")
            
            for i, msg in enumerate(messages):
                if i % 50 == 0:
                    print(f"Processing email {i+1}/{len(messages)}...")
                
                email = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                labels = email.get('labelIds', [])
                status = "UNREAD" if 'UNREAD' in labels else "READ"
                
                snippet = email.get('snippet', 'No preview available')
                
                email_summaries.append(f"""
Email {i+1} ({status}):
From: {sender}
Subject: {subject}
Date: {date}
Preview: {snippet[:100]}{'...' if len(snippet) > 100 else ''}
---""")                 
            
            return f"Bulk fetch complete! Found {len(messages)} emails in {label}:\n" + "\n".join(email_summaries)
            
        except Exception as e:
            return f"Error in bulk fetch: {str(e)}"

    def search_emails_by_sender(self, sender_email: str) -> str:
        """Search emails from a specific sender"""
        try:
            query = f"from:{sender_email}"
            return self.search_emails_simple(query)
        except Exception as e:
            return f"Error searching by sender: {str(e)}"

    def search_emails_by_subject(self, subject_text: str) -> str:
        """Search emails by subject line"""
        try:
            query = f"subject:{subject_text}"
            return self.search_emails_simple(query)
        except Exception as e:
            return f"Error searching by subject: {str(e)}"

    def search_emails_simple(self, query: str) -> str:
        """Search emails using Gmail search syntax"""
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=50
            ).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return f"No emails found matching query: '{query}'"
            
            email_details = []
            for i, msg in enumerate(messages):
                email = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                labels = email.get('labelIds', [])
                status = "UNREAD" if 'UNREAD' in labels else "READ"
                
                snippet = email.get('snippet', 'No preview available')
                
                email_details.append(f"""
Search Result {i+1} ({status}):
ID: {msg['id']}
From: {sender}
Subject: {subject}
Date: {date}
Preview: {snippet}
---""")
            
            return f"Search results for '{query}' ({len(messages)} emails found):\n" + "\n".join(email_details)
            
        except Exception as e:
            return f"Error searching emails: {str(e)}"

agent = Agent(
    model=Ollama(id="llama3.2:latest"),
    name="Gmail Assistant",
    description="""You are a Gmail assistant. You can:
- Read unread emails with read_emails()
- Read recent emails with read_recent_emails_simple()
- Send emails
- Get email details with get_email_details(email_id)
- Search emails with search_emails_simple(query)
- Extract full email content with extract_email_content(email_id)

For order detection, return JSON:
{"order_received": "true/false", "pdf_link": "url_if_found"}

Remember our conversation and reference previous messages naturally.""",
    show_tool_calls=True,
    tools=[GmailTools()],
    memory=AgentMemory(
        db_file="gmail_agent_memory.db",
        table_name="agent_sessions"
    ),
    add_history_to_messages=True,
    num_history_responses=10
)

if __name__ == "__main__":
    print("Gmail Assistant is ready!")
    print("Type 'exit' to quit.\n")
    
    while True:
        user_input = input("Your request: ")
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
        
        try:
            agent.print_response(user_input)
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Please try again or type 'exit' to quit.")