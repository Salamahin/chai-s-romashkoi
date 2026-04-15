from __future__ import annotations

from collections.abc import Generator
from typing import Any

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
