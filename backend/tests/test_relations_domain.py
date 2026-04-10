from __future__ import annotations

import pytest

from relations.domain import build_confirmed_records, build_send_records, normalise_label

SENDER = "alice@example.com"
RECIPIENT = "bob@example.com"
LABEL = "  Friend  "
RELATION_ID = "test-relation-id-001"
CREATED_AT = "2026-04-10T12:00:00Z"


def test_normalise_label_strips_and_lowercases() -> None:
    assert normalise_label("  Friend  ") == "friend"
    assert normalise_label("COLLEAGUE") == "colleague"
    assert normalise_label("  Mixed Case  ") == "mixed case"


def test_build_send_records_creates_correct_pair() -> None:
    sender_copy, recipient_copy = build_send_records(SENDER, RECIPIENT, LABEL, RELATION_ID, CREATED_AT)

    assert sender_copy.owner_email == SENDER
    assert sender_copy.peer_email == RECIPIENT
    assert sender_copy.label == "friend"
    assert sender_copy.status == "pending"
    assert sender_copy.direction == "sent"
    assert sender_copy.relation_id == RELATION_ID
    assert sender_copy.created_at == CREATED_AT

    assert recipient_copy.owner_email == RECIPIENT
    assert recipient_copy.peer_email == SENDER
    assert recipient_copy.label == "friend"
    assert recipient_copy.status == "pending"
    assert recipient_copy.direction == "received"
    assert recipient_copy.relation_id == RELATION_ID
    assert recipient_copy.created_at == CREATED_AT


def test_build_send_records_raises_for_same_email() -> None:
    with pytest.raises(ValueError, match="differ"):
        build_send_records(SENDER, SENDER, LABEL, RELATION_ID, CREATED_AT)


def test_build_confirmed_records_sets_both_to_confirmed() -> None:
    sender_copy, recipient_copy = build_send_records(SENDER, RECIPIENT, LABEL, RELATION_ID, CREATED_AT)
    confirmed_sent, confirmed_received = build_confirmed_records(sender_copy, recipient_copy)

    assert confirmed_sent.status == "confirmed"
    assert confirmed_sent.direction == "sent"
    assert confirmed_received.status == "confirmed"
    assert confirmed_received.direction == "received"

    # Other fields unchanged
    assert confirmed_sent.relation_id == RELATION_ID
    assert confirmed_received.relation_id == RELATION_ID
    assert confirmed_sent.owner_email == SENDER
    assert confirmed_received.owner_email == RECIPIENT


def test_build_confirmed_records_raises_if_not_pending() -> None:
    sender_copy, recipient_copy = build_send_records(SENDER, RECIPIENT, LABEL, RELATION_ID, CREATED_AT)
    confirmed_sent, confirmed_received = build_confirmed_records(sender_copy, recipient_copy)

    with pytest.raises(ValueError, match="pending"):
        build_confirmed_records(confirmed_sent, confirmed_received)

    with pytest.raises(ValueError, match="pending"):
        build_confirmed_records(confirmed_sent, recipient_copy)

    with pytest.raises(ValueError, match="pending"):
        build_confirmed_records(sender_copy, confirmed_received)
