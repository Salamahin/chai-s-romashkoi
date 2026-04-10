from __future__ import annotations

from profile.domain import Profile, ProfileEntry, ProfilePatch
from profile.repository import ProfileRepository

import boto3
import pytest
from moto import mock_aws

TABLE_NAME = "profiles"

ENTRY_A = ProfileEntry(
    entry_id="01AAAAAAAAAAAAAAAAAAAAAAAA", tag="food", text="sushi", updated_at="2026-01-01T00:00:00Z"
)
ENTRY_B = ProfileEntry(
    entry_id="01BBBBBBBBBBBBBBBBBBBBBBBB", tag="sport", text="climbing", updated_at="2026-01-02T00:00:00Z"
)
ENTRY_C = ProfileEntry(
    entry_id="01CCCCCCCCCCCCCCCCCCCCCCCC", tag="music", text="jazz", updated_at="2026-01-03T00:00:00Z"
)


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
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield t


def test_get_returns_empty_profile_for_new_user(table):
    repo = ProfileRepository(table)
    assert repo.get("user1") == Profile(user_sub="user1", entries=())


def test_upsert_and_get_roundtrip(table):
    repo = ProfileRepository(table)
    patch = ProfilePatch(upserted=(ENTRY_A, ENTRY_B), deleted_ids=())
    repo.apply("user1", patch)

    profile = repo.get("user1")
    assert profile == Profile(user_sub="user1", entries=(ENTRY_A, ENTRY_B))


def test_get_returns_entries_sorted_by_entry_id(table):
    repo = ProfileRepository(table)
    # Insert in reverse order — result must still be sorted by SK (ULID).
    patch = ProfilePatch(upserted=(ENTRY_C, ENTRY_A, ENTRY_B), deleted_ids=())
    repo.apply("user1", patch)

    profile = repo.get("user1")
    assert profile.entries == (ENTRY_A, ENTRY_B, ENTRY_C)


def test_upsert_overwrites_existing_entry(table):
    repo = ProfileRepository(table)
    repo.apply("user1", ProfilePatch(upserted=(ENTRY_A,), deleted_ids=()))

    updated = ProfileEntry(
        entry_id=ENTRY_A.entry_id, tag="snacks", text="chips", updated_at="2026-02-01T00:00:00Z"
    )
    repo.apply("user1", ProfilePatch(upserted=(updated,), deleted_ids=()))

    profile = repo.get("user1")
    assert profile.entries == (updated,)


def test_delete_removes_entry(table):
    repo = ProfileRepository(table)
    repo.apply("user1", ProfilePatch(upserted=(ENTRY_A, ENTRY_B), deleted_ids=()))
    repo.apply("user1", ProfilePatch(upserted=(), deleted_ids=(ENTRY_A.entry_id,)))

    profile = repo.get("user1")
    assert profile.entries == (ENTRY_B,)


def test_delete_nonexistent_entry_is_a_noop(table):
    repo = ProfileRepository(table)
    repo.apply("user1", ProfilePatch(upserted=(ENTRY_A,), deleted_ids=()))
    repo.apply("user1", ProfilePatch(upserted=(), deleted_ids=("nonexistent-id",)))

    profile = repo.get("user1")
    assert profile.entries == (ENTRY_A,)


def test_users_are_isolated(table):
    repo = ProfileRepository(table)
    repo.apply("user1", ProfilePatch(upserted=(ENTRY_A,), deleted_ids=()))
    repo.apply("user2", ProfilePatch(upserted=(ENTRY_B,), deleted_ids=()))

    assert repo.get("user1") == Profile(user_sub="user1", entries=(ENTRY_A,))
    assert repo.get("user2") == Profile(user_sub="user2", entries=(ENTRY_B,))
