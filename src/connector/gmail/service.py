import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.db.models import OAuthToken
from src.ingestion.schemas import (
    EmailMetadata,
    FullEmailThread,
    FullThreadFetchResult,
    ThreadIndex,
)
from src.ingestion.utils import extract_participants, normalise_full_message


def fetch_emails(
    token: OAuthToken,
    time_span: str,
    query: str,
    max_results: int = 500,
) -> list[EmailMetadata]:

    if not query.strip():
        raise ValueError("Gmail search query cannot be empty")

    credentials = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri=os.environ.get(
            "GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"
        ),
        client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        scopes=token.scope.split() if token.scope else None,
    )

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )

    emails: list[EmailMetadata] = []
    page_token = None

    while True:
        params = {
            "userId": "me",
            "q": f"newer_than:{time_span} {query}",
            "maxResults": max_results,
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
                    metadataHeaders=[
                        "Subject",
                        "From",
                        "To",
                        "Cc",
                        "Bcc",
                        "Date",
                        "Reply-To",
                        "Message-ID",
                        "In-Reply-To",
                        "References",
                        "List-ID",
                        "List-Unsubscribe",
                        "Precedence",
                        "Auto-Submitted",
                    ],
                )
                .execute()
            )

            headers = {
                h["name"].lower(): h["value"]
                for h in detail.get("payload", {}).get("headers", [])
            }

            label_ids = detail.get("labelIds", [])

            emails.append(
                EmailMetadata(
                    id=detail["id"],
                    thread_id=detail.get("threadId"),
                    from_address=headers.get("from"),
                    to=headers.get("to"),
                    cc=headers.get("cc"),
                    bcc=headers.get("bcc"),
                    reply_to=headers.get("reply-to"),
                    subject=headers.get("subject"),
                    date=headers.get("date"),
                    message_id=headers.get("message-id"),
                    in_reply_to=headers.get("in-reply-to"),
                    references=headers.get("references"),
                    list_id=headers.get("list-id"),
                    list_unsubscribe=headers.get("list-unsubscribe"),
                    precedence=headers.get("precedence"),
                    auto_submitted=headers.get("auto-submitted"),
                    label_ids=label_ids,
                    internal_date=(
                        int(detail["internalDate"])
                        if detail.get("internalDate")
                        else None
                    ),
                    size_estimate=detail.get("sizeEstimate"),
                    snippet=detail.get("snippet"),
                    direction=("outgoing" if "SENT" in label_ids else "incoming"),
                )
            )

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return emails


def fetch_full_threads(
    token: OAuthToken,
    thread_index: ThreadIndex,
) -> FullThreadFetchResult:

    credentials = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri=os.environ.get(
            "GOOGLE_TOKEN_URI",
            "https://oauth2.googleapis.com/token",
        ),
        client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        scopes=token.scope.split() if token.scope else None,
    )

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )

    full_threads = []

    for indexed_thread in thread_index.threads:
        # Fetch the complete conversation using its Gmail thread ID.
        raw_thread = (
            service.users()
            .threads()
            .get(
                userId="me",
                id=indexed_thread.thread_id,
                format="full",
            )
            .execute()
        )

        messages = [
            normalise_full_message(raw_message)
            for raw_message in raw_thread.get("messages", [])
        ]

        # Sort using Gmail's internal timestamp, not the email Date header.
        messages.sort(
            key=lambda m: m.internal_date if m.internal_date is not None else -1
        )

        timestamps = [m.internal_date for m in messages if m.internal_date is not None]

        # Reuse the participant extraction helper from Step 2.
        participants = extract_participants(messages)

        full_threads.append(
            FullEmailThread(
                thread_id=indexed_thread.thread_id,
                discovered_via=indexed_thread.discovered_via,
                messages=messages,
                participants=participants,
                first_interaction_ms=min(timestamps) if timestamps else None,
                last_interaction_ms=max(timestamps) if timestamps else None,
                message_count=len(messages),
            )
        )

    return FullThreadFetchResult(
        threads=full_threads,
        total_threads=len(full_threads),
        total_messages=sum(thread.message_count for thread in full_threads),
    )
