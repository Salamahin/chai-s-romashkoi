from __future__ import annotations

from datetime import datetime
from typing import Any

from boto3.dynamodb.conditions import Key

from log.domain import LogEntry, LogEntryPatch

_PK_PREFIX = "USER#"
_SK_PREFIX = "LOG#"


def _item_to_entry(item: dict[str, Any]) -> LogEntry:
    return LogEntry(
        entry_id=str(item["entry_id"]),
        owner_email=str(item["owner_email"]),
        raw_text=str(item["raw_text"]),
        logged_at=str(item["logged_at"]),
        updated_at=str(item["updated_at"]),
    )


class LogRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def put(self, entry: LogEntry) -> None:
        pk = f"{_PK_PREFIX}{entry.owner_email}"
        sk = f"{_SK_PREFIX}{entry.logged_at}#{entry.entry_id}"
        self._table.put_item(
            Item={
                "PK": pk,
                "SK": sk,
                "owner_email": entry.owner_email,
                "entry_id": entry.entry_id,
                "raw_text": entry.raw_text,
                "logged_at": entry.logged_at,
                "updated_at": entry.updated_at,
            }
        )

    def _query_by_id(self, owner_email: str, entry_id: str) -> dict[str, Any]:
        response = self._table.query(
            IndexName="LogEntryByIdIndex",
            KeyConditionExpression=Key("owner_email").eq(owner_email) & Key("entry_id").eq(entry_id),
        )
        items: list[dict[str, Any]] = response.get("Items", [])
        if not items:
            raise ValueError(f"Entry {entry_id} not found for {owner_email}")
        return items[0]

    def update_text(self, owner_email: str, entry_id: str, patch: LogEntryPatch) -> LogEntry:
        item = self._query_by_id(owner_email, entry_id)
        pk = str(item["PK"])
        sk = str(item["SK"])
        result = self._table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="SET raw_text = :rt, updated_at = :ua",
            ExpressionAttributeValues={":rt": patch.raw_text, ":ua": patch.updated_at},
            ReturnValues="ALL_NEW",
        )
        return _item_to_entry(result["Attributes"])

    def delete(self, owner_email: str, entry_id: str) -> None:
        item = self._query_by_id(owner_email, entry_id)
        pk = str(item["PK"])
        sk = str(item["SK"])
        self._table.delete_item(Key={"PK": pk, "SK": sk})

    def list_window(self, owner_email: str, week_start: str, week_end: str) -> tuple[LogEntry, ...]:
        pk = f"{_PK_PREFIX}{owner_email}"
        # SK is "LOG#<logged_at>#<entry_id>". Use BETWEEN for efficient range scan, then
        # post-filter to enforce the exclusive upper bound on logged_at matching the ADR contract.
        # Use "Z~" suffix on upper bound so DynamoDB's lexicographic BETWEEN includes entries
        # whose second-precision SK ("...T05:13:00Z#uuid") would otherwise sort AFTER a
        # millisecond-precision week_end string ("...T05:13:00.500Z") due to "Z"(90) > "."(46).
        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk)
            & Key("SK").between(
                f"{_SK_PREFIX}{week_start}",
                f"{_SK_PREFIX}{week_end[:19]}Z~",
            ),
        )
        items: list[dict[str, Any]] = response.get("Items", [])
        week_end_dt = datetime.fromisoformat(week_end)
        return tuple(
            _item_to_entry(item)
            for item in items
            if datetime.fromisoformat(str(item.get("logged_at", ""))) < week_end_dt
        )
