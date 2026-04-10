from __future__ import annotations

from profile.domain import Profile

STANDARD_TAGS: list[str] = [
    "food_restrictions",
    "sport_preferences",
    "music_tastes",
    "travel_style",
    "hobbies",
    "languages",
    "fun_facts",
    "looking_for",
    "deal_breakers",
    "pet_peeves",
]


def known_tags(profile: Profile) -> frozenset[str]:
    return frozenset(e.tag for e in profile.entries)
