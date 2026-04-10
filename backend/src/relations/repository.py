from __future__ import annotations

from typing import Any, Literal, cast

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer

from relations.domain import RelationRecord, build_confirmed_records

_PK_PREFIX = "USER#"
_SK_PREFIX = "RELATION#"
_STATUS_DIRECTION_PENDING_RECEIVED = "pending#received"

_serializer = TypeSerializer()


def _serialize(d: dict[str, str]) -> dict[str, Any]:
    return {k: _serializer.serialize(v) for k, v in d.items()}


def _item_to_record(item: dict[str, Any]) -> RelationRecord:
    status_direction = str(item["status_direction"])
    status_part, direction_part = status_direction.split("#", 1)
    status = cast(Literal["pending", "confirmed"], status_part)
    direction = cast(Literal["sent", "received"], direction_part)
    return RelationRecord(
        relation_id=str(item["SK"]).removeprefix(_SK_PREFIX),
        owner_email=str(item["owner_email"]),
        peer_email=str(item["peer_email"]),
        label=str(item["label"]),
        status=status,
        direction=direction,
        created_at=str(item["created_at"]),
    )


def _record_to_raw(record: RelationRecord) -> dict[str, str]:
    return {
        "PK": f"{_PK_PREFIX}{record.owner_email}",
        "SK": f"{_SK_PREFIX}{record.relation_id}",
        "owner_email": record.owner_email,
        "peer_email": record.peer_email,
        "label": record.label,
        "status_direction": f"{record.status}#{record.direction}",
        "created_at": record.created_at,
    }


class RelationRepository:
    def __init__(self, table: Any) -> None:  # boto3 DynamoDB Table resource
        self._table = table
        # Use a fresh DynamoDB client (same region) for transactional writes
        # to avoid double-serialization through the resource event system.
        region = str(table.meta.client.meta.region_name or "us-east-1")
        self._client: Any = boto3.client("dynamodb", region_name=region)

    def list_for_owner(self, owner_email: str) -> tuple[RelationRecord, ...]:
        pk = f"{_PK_PREFIX}{owner_email}"
        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(_SK_PREFIX),
        )
        items: list[dict[str, Any]] = response.get("Items", [])
        records = [_item_to_record(item) for item in items]
        return tuple(sorted(records, key=lambda r: r.created_at))

    def put_pair(self, sender_copy: RelationRecord, recipient_copy: RelationRecord) -> None:
        self._client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": self._table.name,
                        "Item": _serialize(_record_to_raw(sender_copy)),
                    }
                },
                {
                    "Put": {
                        "TableName": self._table.name,
                        "Item": _serialize(_record_to_raw(recipient_copy)),
                    }
                },
            ]
        )

    def confirm_pair(self, confirmer_email: str, relation_id: str) -> RelationRecord:
        pk = f"{_PK_PREFIX}{confirmer_email}"
        sk = f"{_SK_PREFIX}{relation_id}"
        resp = self._table.get_item(Key={"PK": pk, "SK": sk})
        item = resp.get("Item")
        if item is None:
            raise ValueError(f"Relation {relation_id} not found for {confirmer_email}")
        confirmer_record = _item_to_record(item)
        if confirmer_record.direction != "received" or confirmer_record.status != "pending":
            raise ValueError("Only a pending received relation can be confirmed")

        peer_pk = f"{_PK_PREFIX}{confirmer_record.peer_email}"
        peer_resp = self._table.get_item(Key={"PK": peer_pk, "SK": sk})
        peer_item = peer_resp.get("Item")
        if peer_item is None:
            raise ValueError(f"Relation {relation_id} not found for peer {confirmer_record.peer_email}")
        peer_record = _item_to_record(peer_item)

        confirmed_sent, confirmed_received = build_confirmed_records(peer_record, confirmer_record)

        self._client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": self._table.name,
                        "Item": _serialize(_record_to_raw(confirmed_sent)),
                    }
                },
                {
                    "Put": {
                        "TableName": self._table.name,
                        "Item": _serialize(_record_to_raw(confirmed_received)),
                    }
                },
            ]
        )
        return confirmed_received

    def delete_pair(self, owner_email: str, relation_id: str) -> None:
        pk = f"{_PK_PREFIX}{owner_email}"
        sk = f"{_SK_PREFIX}{relation_id}"
        resp = self._table.get_item(Key={"PK": pk, "SK": sk})
        item = resp.get("Item")
        if item is None:
            raise ValueError(f"Relation {relation_id} not found for {owner_email}")
        owner_record = _item_to_record(item)

        peer_pk = f"{_PK_PREFIX}{owner_record.peer_email}"
        peer_resp = self._table.get_item(Key={"PK": peer_pk, "SK": sk})
        peer_item = peer_resp.get("Item")

        if peer_item is None:
            # Peer copy missing — delete only owner's copy
            self._table.delete_item(Key={"PK": pk, "SK": sk})
        else:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Delete": {
                            "TableName": self._table.name,
                            "Key": _serialize({"PK": pk, "SK": sk}),
                        }
                    },
                    {
                        "Delete": {
                            "TableName": self._table.name,
                            "Key": _serialize({"PK": peer_pk, "SK": sk}),
                        }
                    },
                ]
            )

    def count_pending_received(self, owner_email: str) -> int:
        response = self._table.query(
            IndexName="PendingReceivedIndex",
            KeyConditionExpression=(
                Key("owner_email").eq(owner_email) & Key("status_direction").eq(_STATUS_DIRECTION_PENDING_RECEIVED)
            ),
        )
        return int(response.get("Count", 0))
