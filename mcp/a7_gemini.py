

import os
import pickle
import base64
from email.mime.text import MIMEText
from typing import Optional
from phi.memory.agent import AgentMemory
from phi.model.google import Gemini

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.model.google import GeminiOpenAIChat
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
        self.register(self.list_emails)
        self.register(self.get_email)
        self.register(self.send_email)

    def _get_service(self):
        creds = None
        if os.path.exists("token.pkl"):
            with open("token.pkl", "rb") as f:
                creds = pickle.load(f)
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file("cred.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.pkl", "wb") as f:
                pickle.dump(creds, f)
        return build("gmail", "v1", credentials=creds)

    def list_emails(self, query: str = "in:inbox", limit: int = 100) -> str:
        """
        List emails with Gmail search syntax.
        Examples:
          - query="is:unread"
          - query="from:john@example.com"
          - query="subject:meeting"
          - query="after:2024/01/01 before:2024/12/31"
        limit caps results (default 100).
        """
        try:
            messages = []
            next_page = None
            fetched = 0

            while fetched < limit:
                results = self.service.users().messages().list(
                    userId="me", q=query, maxResults=min(100, limit - fetched),
                    pageToken=next_page
                ).execute()
                batch = results.get("messages", [])
                messages.extend(batch)
                fetched += len(batch)
                next_page = results.get("nextPageToken")
                if not next_page or not batch:
                    break

            if not messages:
                return f"No emails found for query: {query}"

            details = []
            for i, msg in enumerate(messages, 1):
                email = self.service.users().messages().get(userId="me", id=msg["id"]).execute()
                headers = email["payload"].get("headers", [])
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
                date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown Date")
                snippet = email.get("snippet", "")
                labels = email.get("labelIds", [])
                status = "UNREAD" if "UNREAD" in labels else "READ"

                details.append(
                    f"[{i}] ({status}) From: {sender} | Subject: {subject} | Date: {date}\nPreview: {snippet[:120]}"
                )
            return "\n".join(details)

        except Exception as e:
            return f"Error listing emails: {str(e)}"

    def get_email(self, email_id: str) -> str:
        """Get full details (headers + decoded body) of a specific email by ID."""
        try:
            email = self.service.users().messages().get(userId="me", id=email_id).execute()
            headers = email["payload"].get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown Date")
            to = next((h["value"] for h in headers if h["name"] == "To"), "Unknown Recipient")

            body = self._extract_email_body(email["payload"])
            return f"From: {sender}\nTo: {to}\nSubject: {subject}\nDate: {date}\n\nBody:\n{body}"

        except Exception as e:
            return f"Error getting email details: {str(e)}"

    def _extract_email_body(self, payload) -> str:
        """Extract plain text from payload (best-effort)."""
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8")
        if payload["mimeType"] == "text/plain":
            data = payload["body"].get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8")
        return "(No plain text body found)"

    def send_email(self, to: str, subject: str, body: str, html: bool = True) -> str:
        """
        Send an email. If html=True, body is wrapped in a clean HTML template.
        """
        try:
            if html:
                html_body = f"""
                <html>
                  <body style="font-family: Arial, sans-serif; line-height:1.6;">
                    <p>{body.replace('\n', '<br>')}</p>
                    <br>
                    <p>Best regards,<br>Your Gmail Assistant</p>
                  </body>
                </html>
                """
                message = MIMEText(html_body, "html")
            else:
                message = MIMEText(body, "plain")

            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return f"Email successfully sent to {to} with subject: {subject}"
        except Exception as e:
            return f"Error sending email: {str(e)}"

# ---------------- Agent Setup ----------------

os.environ["GOOGLE_API_KEY"] = "your_api_key"

agent = Agent(
    model=Gemini(id="models/gemini-1.5-flash-latest"),   # or "gemini-1.5-pro"
    # model=Ollama(id="llama3.2:latest"),

    name="Gmail Assistant",
    show_tool_calls=True,
    api_key = 'your_api_key',
    temperature= 0.2,
    description=
    """You are a Gmail assistant. 
You have GmailTools which lets you safely read and send emails. 
When user asks anything about emails, ALWAYS use GmailTools functions instead of refusing.
Your Job is to look for any new email and see it is realted to any order placement if yes and if it contains any pdf item only return the response in following format strictly:
    {{
        "order_recieved": "true",
        "pdf_link": "return the pdf url from email"
    }}
if you find nothing realted to orders return:
    {{
        "order_recieved": "false",
        "pdf_link": ""
    }}
    """,
    tools=[
        # PythonTools(),
        # GoogleSearch(),
        # Crawl4aiTools(),
        GmailTools()
    ],
    AgentMemory= AgentMemory()
)


# ---------------- Main Loop ----------------
if __name__ == "__main__":
    while True:
        user_input = input("💬 Your request: ")
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("👋 Goodbye!")
            break
        
        try:
            agent.print_response(user_input)
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Please try again or type 'exit' to quit.")
