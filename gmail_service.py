"""
خدمة التعامل مع Gmail API:
- بدء تدفق OAuth2 والحصول على tokens
- جلب آخر الإيميلات من صندوق الوارد
- إرسال رد على إيميل معيّن

ملاحظة: تحتاج ملف credentials.json من Google Cloud Console
(راجع README.md لخطوات الحصول عليه)
"""
import os
import base64
from email.mime.text import MIMEText

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "credentials.json")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")


def build_auth_flow() -> Flow:
    """ينشئ كائن Flow لبدء عملية تسجيل الدخول عبر Google"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    return flow


def get_authorization_url() -> tuple[str, str]:
    """يرجع رابط تسجيل الدخول لعرضه للمستخدم"""
    flow = build_auth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",  # عشان نحصل على refresh_token
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, state


def exchange_code_for_tokens(code: str) -> Credentials:
    """يستبدل authorization code بـ access/refresh tokens بعد موافقة المستخدم"""
    flow = build_auth_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def get_gmail_service(access_token: str, refresh_token: str):
    """يبني كائن Gmail API service من الـ tokens المخزنة"""
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    return build("gmail", "v1", credentials=creds)


def fetch_recent_emails(service, max_results: int = 10) -> list[dict]:
    """يجلب آخر الإيميلات من صندوق الوارد مع المحتوى الأساسي"""
    results = service.users().messages().list(
        userId="me", maxResults=max_results, labelIds=["INBOX"]
    ).execute()
    messages = results.get("messages", [])

    emails = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        body = _extract_body(msg["payload"])

        emails.append({
            "gmail_id": msg["id"],
            "sender": headers.get("From", "unknown"),
            "subject": headers.get("Subject", "(no subject)"),
            "snippet": msg.get("snippet", ""),
            "body": body,
        })
    return emails


def _extract_body(payload: dict) -> str:
    """يستخرج نص الإيميل (يدعم الرسائل متعددة الأجزاء)"""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part["body"].get("data", "")
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        # fallback: أول جزء فيه بيانات
        for part in payload["parts"]:
            if part["body"].get("data"):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""


def send_reply(service, to: str, subject: str, body: str, thread_id: str = None):
    """يرسل رد فعلي عبر Gmail - يُستدعى فقط بعد موافقة المستخدم"""
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    send_body = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id

    return service.users().messages().send(userId="me", body=send_body).execute()
