import os
import re

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.db.models import OAuthToken

_SPAN_PATTERN = re.compile(r"(\d+)([dm])")
MAX_MONTHS = 12
MAX_DAYS = 365


def parse_time_span(value: str) -> str:
    match = _SPAN_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("time span must use days or months, for example 10d or 3m")
    amount, unit = int(match.group(1)), match.group(2)
    if amount == 0:
        raise ValueError("time span must be greater than zero")
    if unit == "m" and amount > MAX_MONTHS:
        raise ValueError("time span cannot exceed 12 months")
    if unit == "d" and amount > MAX_DAYS:
        raise ValueError("time span cannot exceed 365 days")
    return value


def fetch_emails(token: OAuthToken, time_span: str) -> list[dict]:
    credentials = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri=os.environ.get("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        scopes=token.scope.split() if token.scope else None,
    )
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    emails = []
    page_token = None
    while True:
        params = {
            "userId": "me",
            "q": f"newer_than:{time_span}",
            "maxResults": 100,
        }
        if page_token:
            params["pageToken"] = page_token
        response = service.users().messages().list(**params).execute()

        for message in response.get("messages", []):
            detail = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "To", "Date"],
                )
                .execute()
            )
            headers = {
                header["name"]: header["value"]
                for header in detail.get("payload", {}).get("headers", [])
            }
            emails.append(
                {
                    "id": detail["id"],
                    "thread_id": detail.get("threadId"),
                    "subject": headers.get("Subject"),
                    "from": headers.get("From"),
                    "to": headers.get("To"),
                    "date": headers.get("Date"),
                    "snippet": detail.get("snippet"),
                }
            )

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return emails
