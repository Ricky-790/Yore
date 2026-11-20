from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EmailMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    thread_id: str | None = None

    from_address: str | None = Field(default=None, alias="from")
    to: str | None = None
    cc: str | None = None
    bcc: str | None = None
    reply_to: str | None = None

    subject: str | None = None
    date: str | None = None

    message_id: str | None = None
    in_reply_to: str | None = None
    references: str | None = None

    list_id: str | None = None
    list_unsubscribe: str | None = None
    precedence: str | None = None
    auto_submitted: str | None = None

    label_ids: list[str] = Field(default_factory=list)
    internal_date: int | None = None
    size_estimate: int | None = None
    snippet: str | None = None

    direction: Literal["outgoing", "incoming"]


class EmailAttachment(BaseModel):
    part_id: str | None = None
    filename: str | None = None
    mime_type: str
    attachment_id: str | None = None
    size: int = 0
    content_id: str | None = None

    # Some small attachments are embedded directly in the MIME payload.
    inline_data: str | None = None


class FullEmailMessage(EmailMetadata):
    body_text: str = ""
    attachments: list[EmailAttachment] = Field(default_factory=list)
    history_id: str | None = None


class EmailParticipant(BaseModel):
    email: str
    name: str | None = None


class EmailThreadIndex(BaseModel):
    thread_id: str

    # Which discovery passes found messages in this thread
    discovered_via: list[Literal["incoming", "outgoing"]]

    # Only messages discovered in Step 1, not necessarily the full thread
    messages: list[EmailMetadata]

    participants: list[EmailParticipant]

    first_interaction_ms: int | None = None
    last_interaction_ms: int | None = None

    message_count: int


class ThreadIndex(BaseModel):
    threads: list[EmailThreadIndex]

    total_threads: int
    total_messages: int


class FullEmailThread(BaseModel):
    thread_id: str
    discovered_via: list[Literal["incoming", "outgoing"]]

    # Contains every message retrieved from Gmail, not just discovered messages.
    messages: list[FullEmailMessage]

    participants: list[EmailParticipant]

    first_interaction_ms: int | None = None
    last_interaction_ms: int | None = None
    message_count: int


class FullThreadFetchResult(BaseModel):
    threads: list[FullEmailThread]
    total_threads: int
    total_messages: int
