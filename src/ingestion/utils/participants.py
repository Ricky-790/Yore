from email.utils import getaddresses

from src.ingestion.schemas import EmailMetadata, EmailParticipant


def extract_participants(
    messages: list[EmailMetadata],
) -> list[EmailParticipant]:

    participants: dict[str, EmailParticipant] = {}

    for message in messages:
        headers = [
            message.from_address,
            message.to,
            message.cc,
            message.bcc,
        ]

        for header in headers:
            if not header:
                continue

            for name, address in getaddresses([header]):
                address = address.strip()

                if not address or "@" not in address:
                    continue

                key = address.casefold()

                if key not in participants:
                    participants[key] = EmailParticipant(
                        email=address,
                        name=name.strip() or None,
                    )

                elif not participants[key].name and name.strip():
                    participants[key].name = name.strip()

    return sorted(
        participants.values(),
        key=lambda participant: participant.email.casefold(),
    )
