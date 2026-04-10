from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileEntry:
    entry_id: str  # ULID
    tag: str  # normalised (lowercase, stripped)
    text: str
    updated_at: str  # ISO-8601 UTC


@dataclass(frozen=True)
class Profile:
    user_sub: str
    entries: tuple[ProfileEntry, ...]  # sorted by entry_id (ULID order)


@dataclass(frozen=True)
class ProfilePatch:
    upserted: tuple[ProfileEntry, ...]
    deleted_ids: tuple[str, ...]


def normalise_tag(raw: str) -> str:
    return raw.lower().strip()


def normalise_entry(entry: ProfileEntry) -> ProfileEntry:
    return ProfileEntry(
        entry_id=entry.entry_id,
        tag=normalise_tag(entry.tag),
        text=entry.text,
        updated_at=entry.updated_at,
    )


def compute_patch(old: Profile, new: Profile) -> ProfilePatch:
    old_by_id = {e.entry_id: e for e in old.entries}
    new_by_id = {e.entry_id: e for e in new.entries}

    upserted: list[ProfileEntry] = []
    for entry_id, new_entry in new_by_id.items():
        old_entry = old_by_id.get(entry_id)
        if old_entry is None or (
            old_entry.tag != new_entry.tag
            or old_entry.text != new_entry.text
            or old_entry.updated_at != new_entry.updated_at
        ):
            upserted.append(new_entry)

    deleted_ids = tuple(entry_id for entry_id in old_by_id if entry_id not in new_by_id)

    return ProfilePatch(
        upserted=tuple(upserted),
        deleted_ids=deleted_ids,
    )


def apply_patch(base: Profile, patch: ProfilePatch) -> Profile:
    entries_by_id = {e.entry_id: e for e in base.entries}

    for entry in patch.upserted:
        entries_by_id[entry.entry_id] = entry

    for entry_id in patch.deleted_ids:
        entries_by_id.pop(entry_id, None)

    sorted_entries = tuple(sorted(entries_by_id.values(), key=lambda e: e.entry_id))

    return Profile(user_sub=base.user_sub, entries=sorted_entries)
