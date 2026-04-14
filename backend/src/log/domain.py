from __future__ import annotations

import dataclasses
from dataclasses import dataclass


@dataclass(frozen=True)
class LogEntry:
    entry_id: str  # UUID4
    owner_email: str
    raw_text: str
    logged_at: str  # ISO-8601 UTC, second precision, e.g. "2026-04-11T14:05:00Z"
    updated_at: str  # ISO-8601 UTC; equals logged_at on creation


@dataclass(frozen=True)
class LogEntryPatch:
    raw_text: str
    updated_at: str


def to_response_dict(entry: LogEntry) -> dict[str, str]:
    return {
        "entry_id": entry.entry_id,
        "raw_text": entry.raw_text,
        "logged_at": entry.logged_at,
        "updated_at": entry.updated_at,
    }


def make_entry(entry_id: str, owner_email: str, raw_text: str, now: str) -> LogEntry:
    return LogEntry(
        entry_id=entry_id,
        owner_email=owner_email,
        raw_text=raw_text,
        logged_at=now,
        updated_at=now,
    )


def apply_patch(entry: LogEntry, patch: LogEntryPatch) -> LogEntry:
    return dataclasses.replace(entry, raw_text=patch.raw_text, updated_at=patch.updated_at)
