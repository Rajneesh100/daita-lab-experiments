import os
import pickle
import base64
from email.mime.text import MIMEText

from phi.agent import Agent, Tool
from phi.model.ollama import Ollama
from phi.tools.python import PythonTools
from phi.tools.googlesearch import GoogleSearch
from phi.tools.crawl4ai_tools import Crawl4aiTools

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import ClassVar

# ---------------- Gmail OAuth Setup ----------------
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def get_gmail_service():
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

service = get_gmail_service()

# ---------------- Gmail Functions ----------------
def read_emails():
    """Fetch unread emails and return snippets"""
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread').execute()
    messages = results.get('messages', [])
    if not messages:
        return "No unread emails."
    emails = []
    for msg in messages:
        email = service.users().messages().get(userId='me', id=msg['id']).execute()
        emails.append(email.get('snippet'))
    return "\n".join(emails)

def send_email(to: str, subject: str, body: str):
    """Send an email via Gmail"""
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return f"Email sent to {to}."

# ---------------- Custom Phi Tools ----------------
class GmailReadTool(Tool):
    name: ClassVar[str] = "read_emails"
    description: ClassVar[str] = "Fetch unread emails from Gmail"
    type: ClassVar[str] = "function"

    def __call__(self):
        return read_emails()

class GmailSendTool(Tool):
    name: ClassVar[str] = "send_email"
    description: ClassVar[str] = "Send an email via Gmail. Parameters: to (str), subject (str), body (str)"
    type: ClassVar[str] = "function"

    def __call__(self, to: str, subject: str, body: str):
        return send_email(to, subject, body)

# ---------------- Phi Agent Setup ----------------
agent = Agent(
    model=Ollama(id="llama3.2:latest"),
    name="Gmail Agent",
    role="You are an assistant that can read and send Gmail emails using tools.",
    show_tool_calls=True,
    tools=[
        PythonTools(),
        GoogleSearch(),
        Crawl4aiTools(),
        GmailReadTool(),
        GmailSendTool()
    ]
)

# ---------------- Main Loop ----------------
while True:
    user_input = input("Enter your query (or 'exit'): ")
    if user_input.lower() == 'exit':
        break
    agent.print_response(user_input)
