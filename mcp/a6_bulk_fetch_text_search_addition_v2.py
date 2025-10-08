import os
import pickle
import base64
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

# ---------------- Gmail Toolkit ----------------
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
            for msg in messages[:5]:  # Limit to 5 emails for better readability
                email = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                
                # Extract headers
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Get snippet
                snippet = email.get('snippet', 'No preview available')
                
                email_details.append(f"""
                    Email {len(email_details) + 1}:
                    From: {sender}
                    Subject: {subject}
                    Date: {date}
                    Preview: {snippet}
                ---""")
            
            return f"Found {len(messages)} unread emails. Here are the details:\n" + "\n".join(email_details)
            
        except Exception as e:
            return f"Error reading emails: {str(e)}"

    def read_recent_emails_simple(self) -> str:
        """Fetch recent emails (read and unread) from inbox - simple version without limit parameter"""
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
                
                # Extract headers
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Check if unread
                labels = email.get('labelIds', [])
                status = "UNREAD" if 'UNREAD' in labels else "READ"
                
                # Get snippet
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
            
            # Extract headers
            headers = email['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            to = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
            
            # Get body content
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

    def _extract_email_body(self, payload) -> str:
        """Extract email body from payload"""
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
            return f"✅ Email successfully sent to {to} with subject: '{subject}'"
        except Exception as e:
            return f"❌ Error sending email: {str(e)}"

    def bulk_fetch_emails(self, limit: int = 1000, label: str = "INBOX") -> str:
        """Bulk fetch emails with configurable limit (max 1000)"""
        try:
            if limit > 1000:
                limit = 1000
                print("⚠️ Limit capped at 1000 emails for performance")
            
            results = self.service.users().messages().list(
                userId='me', labelIds=[label], maxResults=limit
            ).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return f"No emails found in {label}."
            
            email_summaries = []
            print(f"📧 Fetching {len(messages)} emails...")
            
            for i, msg in enumerate(messages):
                if i % 50 == 0:  # Progress indicator every 50 emails
                    print(f"Processing email {i+1}/{len(messages)}...")
                
                email = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                
                # Extract headers
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Check if unread
                labels = email.get('labelIds', [])
                status = "UNREAD" if 'UNREAD' in labels else "READ"
                
                # Get snippet
                snippet = email.get('snippet', 'No preview available')
                
                email_summaries.append(f"""
                Email {i+1} ({status}):
                From: {sender}
                Subject: {subject}
                Date: {date}
                Preview: {snippet[:100]}{'...' if len(snippet) > 100 else ''}
                ---""")                 
            
            return f"📊 Bulk fetch complete! Found {len(messages)} emails in {label}:\n" + "\n".join(email_summaries)
            
        except Exception as e:
            return f"❌ Error in bulk fetch: {str(e)}"

    def search_emails_by_sender(self, sender_email: str) -> str:
        """Search emails from a specific sender"""
        try:
            query = f"from:{sender_email}"
            return self.search_emails_simple(query)
        except Exception as e:
            return f"❌ Error searching by sender: {str(e)}"

    def search_emails_by_subject(self, subject_text: str) -> str:
        """Search emails by subject line"""
        try:
            query = f"subject:{subject_text}"
            return self.search_emails_simple(query)
        except Exception as e:
            return f"❌ Error searching by subject: {str(e)}"

    def search_emails_simple(self, query: str) -> str:
        """Search emails using Gmail search syntax (simple version without limit parameter)"""
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
                
                # Extract headers
                headers = email['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Check if unread
                labels = email.get('labelIds', [])
                status = "UNREAD" if 'UNREAD' in labels else "READ"
                
                # Get snippet
                snippet = email.get('snippet', 'No preview available')
                
                email_details.append(f"""
Search Result {i+1} ({status}):
From: {sender}
Subject: {subject}
Date: {date}
Preview: {snippet}
---""")
            
            return f"🔍 Search results for '{query}' ({len(messages)} emails found):\n" + "\n".join(email_details)
            
        except Exception as e:
            return f"❌ Error searching emails: {str(e)}"

# ---------------- Agent Setup ----------------


agent = Agent(
    model=Ollama(id="llama3.2:latest"),
    name="Gmail Assistant",
    descryption=f"""You are a powerful Gmail assistant that can:
- Read unread emails and provide detailed summaries with read_emails function
- Read recent emails from inbox with read_recent_emails_simple function
- Send emails to recipients
- Get detailed information about specific emails
- Bulk fetch up to 1000 emails with progress tracking
- Search emails using Gmail search syntax with search_emails_simple function
- Search emails by specific sender with search_emails_by_sender function
- Search emails by subject with search_emails_by_subject function

IMPORTANT: Always use:
- read_emails() for unread emails
- read_recent_emails_simple() for recent emails
- search_emails_simple(query) for general searches
- search_emails_by_sender(sender_email) for sender searches
- search_emails_by_subject(subject_text) for subject searches

Gmail Search Syntax Examples for search_emails_simple:
- "from:john@example.com" - emails from specific sender
- "subject:meeting" - emails with "meeting" in subject
- "is:unread" - unread emails only
- "has:attachment" - emails with attachments
- "after:2024/1/1" - emails after specific date
- "before:2024/12/31" - emails before specific date
- "label:important" - emails with specific label
- "in:inbox" - emails in inbox
- "in:sent" - sent emails
- "in:trash" - emails in trash
- "in:spam" - emails in spam
- "size:larger_than:5M" - emails larger than 5MB
- "filename:pdf" - emails with PDF attachments

When reading emails, provide clear summaries with sender, subject, date, and preview.
When sending emails, confirm the details before sending.
For bulk operations, show progress indicators.
Always be helpful and provide clear, actionable information.
""",
    show_tool_calls=True,
    tools=[
        # PythonTools(),
        # GoogleSearch(),
        # Crawl4aiTools(),
        GmailTools()
    ],
    memeory= AgentMemory()

)

# ---------------- Main Loop ----------------
if __name__ == "__main__":
    print("🤖 Gmail Assistant is ready!")
    print("You can ask me to:")
    print("- Read your unread emails")
    print("- Read recent emails")
    print("- Send emails")
    print("- Get details about specific emails")
    print("- Bulk fetch up to 1000 emails")
    print("- Search emails using Gmail search syntax")
    print("- Search emails by sender or subject")
    print("\n🔍 Gmail Search Examples:")
    print("- 'Search emails from john@example.com'")
    print("- 'Find emails with subject containing meeting'")
    print("- 'Show me unread emails'")
    print("- 'Search emails after 2024/1/1'")
    print("- 'Find emails with attachments'")
    print("\nType 'exit' to quit.\n")
    
    while True:
        user_input = input("💬 Your request: ")
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("👋 Goodbye!")
            break
        
        try:
            agent.print_response(user_input)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("Please try again or type 'exit' to quit.")
