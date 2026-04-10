from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from relations.domain import build_send_records
from relations.repository import RelationRepository

TABLE_NAME = "relations"

SENDER = "alice@example.com"
RECIPIENT = "bob@example.com"
LABEL = "friend"
RELATION_ID = "test-relation-id-001"
CREATED_AT = "2026-04-10T12:00:00Z"


@pytest.fixture
def table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        t = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "owner_email", "AttributeType": "S"},
                {"AttributeName": "status_direction", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "PendingReceivedIndex",
                    "KeySchema": [
                        {"AttributeName": "owner_email", "KeyType": "HASH"},
                        {"AttributeName": "status_direction", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )
        yield t


def _make_pair(
    sender: str = SENDER,
    recipient: str = RECIPIENT,
    label: str = LABEL,
    relation_id: str = RELATION_ID,
    created_at: str = CREATED_AT,
) -> tuple:
    return build_send_records(sender, recipient, label, relation_id, created_at)


def test_put_pair_then_list_for_owner(table) -> None:
    repo = RelationRepository(table)
    sender_copy, recipient_copy = _make_pair()
    repo.put_pair(sender_copy, recipient_copy)

    sender_records = repo.list_for_owner(SENDER)
    assert len(sender_records) == 1
    assert sender_records[0] == sender_copy

    recipient_records = repo.list_for_owner(RECIPIENT)
    assert len(recipient_records) == 1
    assert recipient_records[0] == recipient_copy


def test_confirm_pair_updates_status(table) -> None:
    repo = RelationRepository(table)
    sender_copy, recipient_copy = _make_pair()
    repo.put_pair(sender_copy, recipient_copy)

    repo.confirm_pair(RECIPIENT, RELATION_ID)

    sender_records = repo.list_for_owner(SENDER)
    assert sender_records[0].status == "confirmed"
    assert sender_records[0].direction == "sent"

    recipient_records = repo.list_for_owner(RECIPIENT)
    assert recipient_records[0].status == "confirmed"
    assert recipient_records[0].direction == "received"


def test_delete_pair_removes_both_copies(table) -> None:
    repo = RelationRepository(table)
    sender_copy, recipient_copy = _make_pair()
    repo.put_pair(sender_copy, recipient_copy)

    repo.delete_pair(SENDER, RELATION_ID)

    assert repo.list_for_owner(SENDER) == ()
    assert repo.list_for_owner(RECIPIENT) == ()


def test_count_pending_received_for_recipient_is_one(table) -> None:
    repo = RelationRepository(table)
    sender_copy, recipient_copy = _make_pair()
    repo.put_pair(sender_copy, recipient_copy)

    assert repo.count_pending_received(RECIPIENT) == 1
    assert repo.count_pending_received(SENDER) == 0


def test_count_pending_received_is_zero_after_confirm(table) -> None:
    repo = RelationRepository(table)
    sender_copy, recipient_copy = _make_pair()
    repo.put_pair(sender_copy, recipient_copy)

    repo.confirm_pair(RECIPIENT, RELATION_ID)

    assert repo.count_pending_received(RECIPIENT) == 0
