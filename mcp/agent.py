# import pickle
# import base64
# from email.mime.text import MIMEText

# from phi.agent import Agent
# from phi.model.ollama import Ollama
# from phi.tools.python import PythonTools
# from phi.tools.googlesearch import GoogleSearch
# from phi.tools.crawl4ai_tools import Crawl4aiTools

# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build

# # ---------------- Gmail Setup ----------------
# SCOPES = [
#     'https://www.googleapis.com/auth/gmail.readonly',
#     'https://www.googleapis.com/auth/gmail.send'
# ]

# def get_gmail_service():
#     creds = None
#     try:
#         with open('token.pkl', 'rb') as f:
#             creds = pickle.load(f)
#     except FileNotFoundError:
#         flow = InstalledAppFlow.from_client_secrets_file('cred.json', SCOPES)
#         creds = flow.run_local_server(port=0)
#         with open('token.pkl', 'wb') as f:
#             pickle.dump(creds, f)
#     return build('gmail', 'v1', credentials=creds)

# service = get_gmail_service()

# # Read unread emails
# def read_emails():
#     results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread').execute()
#     messages = results.get('messages', [])
#     emails = []
#     for msg in messages:
#         email = service.users().messages().get(userId='me', id=msg['id']).execute()
#         snippet = email.get('snippet')
#         emails.append(snippet)
#     return emails

# # Send email
# def send_email(to, subject, body):
#     message = MIMEText(body)
#     message['to'] = to
#     message['subject'] = subject
#     raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
#     service.users().messages().send(userId='me', body={'raw': raw}).execute()
#     return f"Email sent to {to}."

# # ---------------- Phi Agent Setup ----------------
# agent = Agent(
#     model=Ollama(id="llama3.2:latest"),
#     name="Email Reader",
#     role="you are a helpful agent observe user email and help him with him queries",
#     show_tool_calls=True,
#     tools=[PythonTools(), GoogleSearch(), Crawl4aiTools()]
# )

# # Add Gmail tools to agent
# agent.tools.append({
#     "name": "read_emails",
#     "description": "Fetch unread emails from Gmail.",
#     "func": read_emails
# })
# agent.tools.append({
#     "name": "send_email",
#     "description": "Send an email via Gmail. Usage: send_email(to, subject, body)",
#     "func": send_email
# })

# # ---------------- Main Loop ----------------
# while True:
#     user_input = input("Enter your query (or 'exit'): ")
#     if user_input.lower() == 'exit':
#         break
    
#     response = agent.print_response(user_input)
import os
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


# ---------------- Gmail OAuth Setup ----------------
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def get_gmail_service():
    creds = None
    # Token file stores the user’s access and refresh tokens
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
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread').execute()
    messages = results.get('messages', [])
    emails = []
    for msg in messages:
        email = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = email.get('snippet')
        emails.append(snippet)
    return emails

def send_email(to, subject, body):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return f"Email sent to {to}."

# ---------------- Phi Agent ----------------
agent = Agent(
    model=Ollama(id="llama3.2:latest"),
    name="Gmail Agent",
    role="You are a helpful agent that can read and send Gmail messages.",
    show_tool_calls=True,
    tools=[PythonTools(), GoogleSearch(), Crawl4aiTools()]
)


# from phi.tools.python import PythonTool

# Wrap Gmail functions using PythonTool
read_emails_tool = PythonTool(
    func=read_emails,
    name="read_emails",
    description="Fetch unread emails from Gmail"
)

send_email_tool = PythonTool(
    func=send_email,
    name="send_email",
    description="Send an email via Gmail. Usage: send_email(to, subject, body)"
)

agent.tools.append(read_emails_tool)
agent.tools.append(send_email_tool)


# ---------------- Main Loop ----------------
while True:
    user_input = input("Enter your query (or 'exit'): ")
    if user_input.lower() == 'exit':
        break
    
    agent.print_response(user_input)
