import base64
from email.message import Message as MIMEMessage
from html.parser import HTMLParser
from typing import ClassVar

from src.ingestion.schemas import EmailAttachment, FullEmailMessage


def decode_body(data: str) -> bytes:
    # Restore Base64 padding before decoding.
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


class HTMLTextExtractor(HTMLParser):
    BLOCK_TAGS: ClassVar = {
        "p",
        "div",
        "br",
        "li",
        "tr",
        "h1",
        "h2",
        "h3",
        "h4",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip_depth += 1
        elif not self.skip_depth and tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.text_parts.append(data)


def html_to_text(html: str) -> str:
    parser = HTMLTextExtractor()
    parser.feed(html)

    # Remove excessive whitespace while retaining paragraph breaks.
    lines = [" ".join(line.split()) for line in "".join(parser.text_parts).splitlines()]

    return "\n".join(line for line in lines if line).strip()


def extract_mime_content(
    part: dict,
    plain_parts: list[str],
    html_parts: list[str],
    other_text_parts: list[str],
    attachments: list[EmailAttachment],
):
    mime_type = part.get("mimeType", "")
    filename = part.get("filename")
    body = part.get("body", {})
    headers = {h["name"].lower(): h["value"] for h in part.get("headers", [])}

    attachment_id = body.get("attachmentId")
    data = body.get("data")

    disposition = headers.get("content-disposition", "")
    content_id = headers.get("content-id")

    is_attachment = (
        bool(filename)
        or bool(attachment_id)
        or disposition.lower().startswith("attachment")
    )

    if is_attachment:
        attachments.append(
            EmailAttachment(
                part_id=part.get("partId"),
                filename=filename,
                mime_type=mime_type,
                attachment_id=attachment_id,
                size=body.get("size", 0),
                content_id=content_id,
                inline_data=data if data and not attachment_id else None,
            )
        )
        return

    # Decode text content, but leave binary attachments untouched.
    if data:
        content_type = MIMEMessage()
        if headers.get("content-type"):
            content_type["Content-Type"] = headers["content-type"]

        charset = content_type.get_content_charset() or "utf-8"

        try:
            content = decode_body(data).decode(charset, errors="replace")
        except LookupError:
            content = decode_body(data).decode("utf-8", errors="replace")

        if mime_type == "text/plain":
            plain_parts.append(content)

        elif mime_type == "text/html":
            html_parts.append(content)

        elif mime_type.startswith("text/"):
            # Preserve other useful text formats, such as text/calendar.
            other_text_parts.append(content)

    # Multipart messages can contain arbitrarily nested MIME structures.
    for child in part.get("parts", []):
        extract_mime_content(
            child,
            plain_parts,
            html_parts,
            other_text_parts,
            attachments,
        )


def normalise_full_message(raw: dict) -> FullEmailMessage:
    headers = {
        h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])
    }

    plain_parts = []
    html_parts = []
    other_text_parts = []
    attachments = []

    # Extract body content and attachments recursively.
    extract_mime_content(
        raw.get("payload", {}),
        plain_parts,
        html_parts,
        other_text_parts,
        attachments,
    )

    # Prefer plain text; use converted HTML when plain text is unavailable.
    if plain_parts:
        body_text = "\n".join(plain_parts + other_text_parts)
    elif html_parts:
        body_text = html_to_text("\n".join(html_parts))

        if other_text_parts:
            body_text += "\n" + "\n".join(other_text_parts)
    else:
        body_text = "\n".join(other_text_parts)

    label_ids = raw.get("labelIds", [])

    return FullEmailMessage(
        id=raw["id"],
        thread_id=raw.get("threadId"),
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
        internal_date=(int(raw["internalDate"]) if raw.get("internalDate") else None),
        size_estimate=raw.get("sizeEstimate"),
        snippet=raw.get("snippet"),
        direction=("outgoing" if "SENT" in label_ids else "incoming"),
        body_text=body_text,
        attachments=attachments,
        history_id=raw.get("historyId"),
    )
