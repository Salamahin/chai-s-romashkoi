from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RelationRecord:
    relation_id: str
    owner_email: str
    peer_email: str
    label: str
    status: Literal["pending", "confirmed"]
    direction: Literal["sent", "received"]
    created_at: str  # ISO-8601 UTC


def normalise_label(raw: str) -> str:
    return raw.lower().strip()


def build_send_records(
    sender_email: str,
    recipient_email: str,
    label: str,
    relation_id: str,
    created_at: str,
) -> tuple[RelationRecord, RelationRecord]:
    if sender_email == recipient_email:
        raise ValueError("sender_email and recipient_email must differ")
    normalised = normalise_label(label)
    sender_copy = RelationRecord(
        relation_id=relation_id,
        owner_email=sender_email,
        peer_email=recipient_email,
        label=normalised,
        status="pending",
        direction="sent",
        created_at=created_at,
    )
    recipient_copy = RelationRecord(
        relation_id=relation_id,
        owner_email=recipient_email,
        peer_email=sender_email,
        label=normalised,
        status="pending",
        direction="received",
        created_at=created_at,
    )
    return sender_copy, recipient_copy


def build_confirmed_records(
    sent_copy: RelationRecord,
    received_copy: RelationRecord,
) -> tuple[RelationRecord, RelationRecord]:
    if sent_copy.status != "pending" or received_copy.status != "pending":
        raise ValueError("Both records must have status=pending to confirm")
    confirmed_sent = dataclasses.replace(sent_copy, status="confirmed")
    confirmed_received = dataclasses.replace(received_copy, status="confirmed")
    return confirmed_sent, confirmed_received
