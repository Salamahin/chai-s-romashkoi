from __future__ import annotations

from profile.domain import Profile, ProfileEntry, ProfilePatch
from typing import Any


class ProfileRepository:
    def __init__(self, table: Any) -> None:  # boto3 DynamoDB Table resource
        self._table = table

    def get(self, user_sub: str) -> Profile:
        pk = f"USER#{user_sub}"
        response = self._table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
            ExpressionAttributeValues={":pk": pk, ":prefix": "ENTRY#"},
        )
        items: list[dict[str, str]] = response.get("Items", [])
        entries = tuple(
            ProfileEntry(
                entry_id=str(item["SK"]).removeprefix("ENTRY#"),
                tag=str(item["tag"]),
                text=str(item["text"]),
                updated_at=str(item["updated_at"]),
            )
            for item in sorted(items, key=lambda i: str(i["SK"]))
        )
        return Profile(user_sub=user_sub, entries=entries)

    def apply(self, user_sub: str, patch: ProfilePatch) -> None:
        pk = f"USER#{user_sub}"
        for entry in patch.upserted:
            self._table.put_item(
                Item={
                    "PK": pk,
                    "SK": f"ENTRY#{entry.entry_id}",
                    "tag": entry.tag,
                    "text": entry.text,
                    "updated_at": entry.updated_at,
                }
            )
        for entry_id in patch.deleted_ids:
            self._table.delete_item(
                Key={
                    "PK": pk,
                    "SK": f"ENTRY#{entry_id}",
                }
            )
