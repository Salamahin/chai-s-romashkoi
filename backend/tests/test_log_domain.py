from __future__ import annotations

from log.domain import LogEntryPatch, apply_patch, make_entry

NOW = "2026-04-11T14:05:00Z"
ENTRY_ID = "abc-123"
OWNER = "alice@example.com"
TEXT = "Hello world"


def test_make_entry_sets_both_timestamps() -> None:
    entry = make_entry(ENTRY_ID, OWNER, TEXT, NOW)
    assert entry.entry_id == ENTRY_ID
    assert entry.owner_email == OWNER
    assert entry.raw_text == TEXT
    assert entry.logged_at == NOW
    assert entry.updated_at == NOW


def test_apply_patch_updates_text_and_updated_at() -> None:
    entry = make_entry(ENTRY_ID, OWNER, TEXT, NOW)
    new_now = "2026-04-11T15:00:00Z"
    patch = LogEntryPatch(raw_text="New text", updated_at=new_now)
    updated = apply_patch(entry, patch)
    assert updated.raw_text == "New text"
    assert updated.updated_at == new_now
    assert updated.logged_at == NOW  # unchanged
    assert updated.entry_id == ENTRY_ID
    assert updated.owner_email == OWNER


def test_apply_patch_returns_new_instance() -> None:
    entry = make_entry(ENTRY_ID, OWNER, TEXT, NOW)
    patch = LogEntryPatch(raw_text="Different", updated_at="2026-04-11T15:00:00Z")
    updated = apply_patch(entry, patch)
    assert updated is not entry
