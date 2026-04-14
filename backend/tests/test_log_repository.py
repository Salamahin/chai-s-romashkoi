from __future__ import annotations

import pytest

from log.domain import LogEntryPatch, make_entry
from log.repository import LogRepository

TABLE_NAME = "profiles"
OWNER = "alice@example.com"
ENTRY_ID = "abc-123"
NOW = "2026-04-11T14:05:00Z"
TEXT = "Hello"


def _make_entry(entry_id: str = ENTRY_ID, owner: str = OWNER, text: str = TEXT, now: str = NOW):  # type: ignore[no-untyped-def]
    return make_entry(entry_id, owner, text, now)


def test_put_then_list_window(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    entry = _make_entry()
    repo.put(entry)
    results = repo.list_window(OWNER, "2026-04-11T00:00:00Z", "2026-04-12T00:00:00Z")
    assert len(results) == 1
    assert results[0] == entry


def test_list_window_excludes_outside_range(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    early = _make_entry(entry_id="e1", now="2026-04-10T12:00:00Z")
    later = _make_entry(entry_id="e2", now="2026-04-12T12:00:00Z")
    repo.put(early)
    repo.put(later)
    results = repo.list_window(OWNER, "2026-04-11T00:00:00Z", "2026-04-12T00:00:00Z")
    assert results == ()


def test_list_window_returns_ascending_order(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    e1 = _make_entry(entry_id="e1", now="2026-04-11T10:00:00Z")
    e2 = _make_entry(entry_id="e2", now="2026-04-11T12:00:00Z")
    repo.put(e2)
    repo.put(e1)
    results = repo.list_window(OWNER, "2026-04-11T00:00:00Z", "2026-04-12T00:00:00Z")
    assert results[0].entry_id == "e1"
    assert results[1].entry_id == "e2"


def test_update_text(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    entry = _make_entry()
    repo.put(entry)
    patch = LogEntryPatch(raw_text="Updated text", updated_at="2026-04-11T15:00:00Z")
    updated = repo.update_text(OWNER, ENTRY_ID, patch)
    assert updated.raw_text == "Updated text"
    assert updated.updated_at == "2026-04-11T15:00:00Z"
    assert updated.logged_at == NOW


def test_update_text_raises_if_not_found(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    patch = LogEntryPatch(raw_text="x", updated_at="2026-04-11T15:00:00Z")
    with pytest.raises(ValueError):
        repo.update_text(OWNER, "nonexistent", patch)


def test_delete(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    entry = _make_entry()
    repo.put(entry)
    repo.delete(OWNER, ENTRY_ID)
    results = repo.list_window(OWNER, "2026-04-11T00:00:00Z", "2026-04-12T00:00:00Z")
    assert results == ()


def test_delete_raises_if_not_found(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    with pytest.raises(ValueError):
        repo.delete(OWNER, "nonexistent")


def test_list_window_returns_empty_for_owner_with_no_entries(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    results = repo.list_window("nobody@example.com", "2026-04-11T00:00:00Z", "2026-04-12T00:00:00Z")
    assert results == ()


def test_list_window_owner_isolation(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    bob_entry = _make_entry(entry_id="e-bob", owner="bob@example.com")
    alice_entry = _make_entry(entry_id="e-alice", owner=OWNER)
    repo.put(bob_entry)
    repo.put(alice_entry)
    results = repo.list_window(OWNER, "2026-04-11T00:00:00Z", "2026-04-12T00:00:00Z")
    assert len(results) == 1
    assert results[0].entry_id == "e-alice"


def test_update_text_persists_in_list_window(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    entry = _make_entry()
    repo.put(entry)
    patch = LogEntryPatch(raw_text="Persisted change", updated_at="2026-04-11T16:00:00Z")
    repo.update_text(OWNER, ENTRY_ID, patch)
    results = repo.list_window(OWNER, "2026-04-11T00:00:00Z", "2026-04-12T00:00:00Z")
    assert results[0].raw_text == "Persisted change"
    assert results[0].updated_at == "2026-04-11T16:00:00Z"
    assert results[0].logged_at == NOW  # unchanged


def test_update_text_wrong_owner_raises(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    entry = _make_entry()
    repo.put(entry)
    patch = LogEntryPatch(raw_text="hacked", updated_at="2026-04-11T16:00:00Z")
    with pytest.raises(ValueError):
        repo.update_text("hacker@example.com", ENTRY_ID, patch)


def test_delete_wrong_owner_raises(table) -> None:  # type: ignore[no-untyped-def]
    repo = LogRepository(table)
    entry = _make_entry()
    repo.put(entry)
    with pytest.raises(ValueError):
        repo.delete("hacker@example.com", ENTRY_ID)


def test_same_second_entries_both_stored(table) -> None:  # type: ignore[no-untyped-def]
    """UUID suffix in SK prevents same-second collision."""
    repo = LogRepository(table)
    e1 = _make_entry(entry_id="uuid-aaa", now="2026-04-11T10:00:00Z")
    e2 = _make_entry(entry_id="uuid-zzz", now="2026-04-11T10:00:00Z")
    repo.put(e1)
    repo.put(e2)
    results = repo.list_window(OWNER, "2026-04-11T00:00:00Z", "2026-04-12T00:00:00Z")
    assert len(results) == 2
