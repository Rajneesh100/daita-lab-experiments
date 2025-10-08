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
        results = self.service.users().messages().list(
            userId='me', labelIds=['INBOX'], q='is:unread'
        ).execute()
        messages = results.get('messages', [])
        if not messages:
            return "No unread emails."
        snippets = []
        for msg in messages:
            email = self.service.users().messages().get(userId='me', id=msg['id']).execute()
            snippets.append(email.get('snippet'))
        return "\n".join(snippets)

    def send_email(self, to: str, subject: str, body: str) -> str:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        self.service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return f"Email sent to {to}."

# ---------------- Agent Setup ----------------
agent = Agent(
    model=Ollama(id="llama3.2:latest"),
    name="Gmail Agent",
    role="You are an assistant that can read and send Gmail emails using tools.",
    show_tool_calls=True,
    tools=[
        PythonTools(),
        GoogleSearch(),
        Crawl4aiTools(),
        GmailTools()  # <-- Gmail tools are now in the same file
    ]
)

# ---------------- Main Loop ----------------
while True:
    # user_input = input("Enter your query (or 'exit'): ")
    # if user_input.lower() == 'exit':
    #     break
    # agent.print_response(user_input)
    to="example@gmail.com"
    subject ="test"
    body ="hello"
    query = input("Enter your query (or 'exit'): ")
    if "read" in query.lower() and "email" in query.lower():
        print(GmailTools().read_emails())
    elif "send" in query.lower() and "email" in query.lower():
        # simple parsing example
        GmailTools().send_email(to, subject, body)
    else:
        agent.print_response(query)

