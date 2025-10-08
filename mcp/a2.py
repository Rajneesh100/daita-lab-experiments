import pickle
import base64
from email.mime.text import MIMEText
from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.python import PythonTools
from phi.tools.googlesearch import GoogleSearch
from phi.tools.crawl4ai_tools import Crawl4aiTools

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

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

# ---------------- Gmail Tool Functions ----------------
def read_emails_tool():
    """Fetch unread emails from Gmail and return snippets."""
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread').execute()
    messages = results.get('messages', [])
    emails = []
    for msg in messages:
        email = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = email.get('snippet')
        emails.append(snippet)
    if not emails:
        return "No unread emails."
    return "\n".join(emails)

def send_email_tool(to: str, subject: str, body: str):
    """Send an email via Gmail."""
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return f"Email sent to {to}."

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
        # Add Gmail tools in proper agentic way
        {
            "name": "read_emails",
            "description": "Fetch unread emails from Gmail.",
            "parameters": {},
            "function": read_emails_tool
        },
        {
            "name": "send_email",
            "description": "Send an email via Gmail. Params: to (str), subject (str), body (str).",
            "parameters": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "function": send_email_tool
        }
    ]
)

# ---------------- Main Loop ----------------
while True:
    user_input = input("Enter your query (or 'exit'): ")
    if user_input.lower() == 'exit':
        break

    # The agent now can invoke read_emails / send_email as a tool
    agent.print_response(user_input)
