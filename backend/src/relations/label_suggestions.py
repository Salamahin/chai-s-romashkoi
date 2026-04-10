from __future__ import annotations

from relations.domain import RelationRecord


def known_labels(records: tuple[RelationRecord, ...]) -> frozenset[str]:
    return frozenset(r.label for r in records)
