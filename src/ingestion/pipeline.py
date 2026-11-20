from collections import defaultdict

from src.connector.gmail import fetch_emails
from src.connector.gmail.service import fetch_full_threads
from src.db.models import OAuthToken
from src.ingestion.schemas import EmailMetadata, EmailThreadIndex, ThreadIndex
from src.ingestion.utils import extract_participants


def get_emails(token: OAuthToken, time_span: str | None) -> tuple[list, list]:
    outgoing = fetch_emails(
        token=token,
        time_span=time_span or "6m",
        query="from:me -category:promotions -category:forums",
    )

    incoming = fetch_emails(
        token=token,
        time_span=time_span or "6m",
        query="(to:me OR cc:me) -from:me -category:promotions -category:forums",
    )
    return (incoming, outgoing)


def build_thread_index(
    incoming: list[EmailMetadata],
    outgoing: list[EmailMetadata],
) -> ThreadIndex:

    # thread_id -> {message_id: EmailMetadata}
    grouped_messages: dict[str, dict[str, EmailMetadata]] = defaultdict(dict)

    # thread_id -> discovery sources
    discovered_sources: dict[str, set[str]] = defaultdict(set)

    # Process both discovery passes
    for source, emails in [
        ("incoming", incoming),
        ("outgoing", outgoing),
    ]:
        for email in emails:
            if not email.thread_id:
                raise ValueError(f"Message {email.id} has no Gmail thread_id")

            thread_id = email.thread_id

            # Record how this thread was discovered
            discovered_sources[thread_id].add(source)

            # Deduplicate messages across both passes
            grouped_messages[thread_id][email.id] = email

    threads = []

    # Construct thread-level records
    for thread_id, message_map in grouped_messages.items():
        messages = sorted(
            message_map.values(),
            key=lambda message: (
                message.internal_date if message.internal_date is not None else -1
            ),
        )

        timestamps = [
            message.internal_date
            for message in messages
            if message.internal_date is not None
        ]

        participants = extract_participants(messages)

        sources = discovered_sources[thread_id]

        threads.append(
            EmailThreadIndex(
                thread_id=thread_id,
                discovered_via=[
                    source for source in ("incoming", "outgoing") if source in sources
                ],
                messages=messages,
                participants=participants,
                first_interaction_ms=min(timestamps) if timestamps else None,
                last_interaction_ms=max(timestamps) if timestamps else None,
                message_count=len(messages),
            )
        )

    # Most recently active threads first
    threads.sort(
        key=lambda thread: (
            thread.last_interaction_ms if thread.last_interaction_ms is not None else -1
        ),
        reverse=True,
    )

    return ThreadIndex(
        threads=threads,
        total_threads=len(threads),
        total_messages=sum(thread.message_count for thread in threads),
    )


# Step 1
incoming, outgoing = get_emails(token, "6m")

# Step 2
thread_index = build_thread_index(
    incoming=incoming,
    outgoing=outgoing,
)

# Step 3
full_thread_data = fetch_full_threads(
    token=token,
    thread_index=thread_index,
)

# Serialise if needed
result = full_thread_data.model_dump(
    mode="json",
    by_alias=True,
)
