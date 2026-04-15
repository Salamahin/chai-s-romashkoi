from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

# Set env vars required by Lambda handlers before they are imported.
# All handler modules read these at module level; setting them here ensures
# they are available regardless of import order during test collection.
os.environ.setdefault("SESSION_SECRET", "test-secret-for-tests")
os.environ.setdefault("PROFILES_TABLE_NAME", "profiles")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")

import boto3
import pytest
from moto import mock_aws

TABLE_NAME = "profiles"


@pytest.fixture
def table() -> Generator[Any, None, None]:
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
                {"AttributeName": "entry_id", "AttributeType": "S"},
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
                },
                {
                    "IndexName": "LogEntryByIdIndex",
                    "KeySchema": [
                        {"AttributeName": "owner_email", "KeyType": "HASH"},
                        {"AttributeName": "entry_id", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        )
        yield t
