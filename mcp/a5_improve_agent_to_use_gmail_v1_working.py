import os
import pickle
import base64
from email.mime.text import MIMEText
from typing import Optional
from phi.memory.agent import AgentMemory

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.python import PythonTools
from phi.tools.googlesearch import GoogleSearch
from phi.tools.crawl4ai_tools import Crawl4aiTools
from phi.tools import Toolkit

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
        self.register(self.read_recent_emails)
        self.register(self.get_email_details)

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

    def read_recent_emails(self, limit: int = 5) -> str:
        """Fetch recent emails (read and unread) from inbox"""
        try:
            results = self.service.users().messages().list(
                userId='me', labelIds=['INBOX'], maxResults=limit
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

# ---------------- Agent Setup ----------------


agent = Agent(
    model=Ollama(id="llama3.2:latest"),
    name="Gmail Assistant",
    role="""You are a helpful Gmail assistant that can:
- Read unread emails and provide detailed summaries
- Read recent emails from inbox
- Send emails to recipients
- Get detailed information about specific emails

When reading emails, provide clear summaries with sender, subject, date, and preview.
When sending emails, confirm the details before sending.
Always be helpful and provide clear, actionable information.""",
    show_tool_calls=True,
    tools=[
        # PythonTools(),
        # GoogleSearch(),
        # Crawl4aiTools(),
        GmailTools()
    ],
    memory=AgentMemory()


)

# ---------------- Main Loop ----------------
if __name__ == "__main__":
    print("🤖 Gmail Assistant is ready!")
    print("You can ask me to:")
    print("- Read your unread emails")
    print("- Read recent emails")
    print("- Send emails")
    print("- Get details about specific emails")
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
