"""Constants for the Eesti Keskkonnateenused integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "keskkonnateenused"

CONF_CONTRACT_NUMBER: Final = "contract_number"

API_URL: Final = "https://cms.keskkonnateenused.ee/wp-json/general-purpose-api/upcoming-discharges"
LOOKUP_URL: Final = "https://www.keskkonnateenused.ee/klienditugi/j%C3%A4rgmine-veop%C3%A4ev"

MANUFACTURER: Final = "Eesti Keskkonnateenused AS"

UPDATE_INTERVAL: Final = timedelta(hours=6)

# Waste categories, matched by lowercase substrings of the provider's waste name.
# Order matters: "klaaspakend" is glass, "segapakendid" is packaging, so the more
# specific categories come before the broader ones.
WASTE_CATEGORIES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("glass", ("klaas",)),
    ("packaging", ("pakend",)),
    ("paper", ("paber", "papp", "kartong")),
    ("bio", ("bio", "köögi", "toidu")),
    ("garden", ("aia", "haljastus")),
    ("bulky", ("suurjäät",)),
    ("hazardous", ("ohtlik",)),
    ("mixed", ("sega", "olme")),
)

CATEGORY_ICONS: Final[dict[str | None, str]] = {
    "glass": "mdi:bottle-wine",
    "packaging": "mdi:recycle-variant",
    "paper": "mdi:package-variant",
    "bio": "mdi:food-apple",
    "garden": "mdi:flower",
    "bulky": "mdi:sofa",
    "hazardous": "mdi:biohazard",
    "mixed": "mdi:trash-can",
    None: "mdi:trash-can-outline",
}

# Calendar event titles. Entity names come from translations/*.json instead.
CATEGORY_NAMES: Final[dict[str, dict[str, str]]] = {
    "en": {
        "glass": "Glass",
        "packaging": "Packaging",
        "paper": "Paper and cardboard",
        "bio": "Biowaste",
        "garden": "Garden waste",
        "bulky": "Bulky waste",
        "hazardous": "Hazardous waste",
        "mixed": "Mixed waste",
    },
    "et": {
        "glass": "Klaas",
        "packaging": "Pakendid",
        "paper": "Paber ja kartong",
        "bio": "Biojäätmed",
        "garden": "Aiajäätmed",
        "bulky": "Suurjäätmed",
        "hazardous": "Ohtlikud jäätmed",
        "mixed": "Segaolmejäätmed",
    },
    "ru": {
        "glass": "Стекло",
        "packaging": "Упаковка",
        "paper": "Бумага и картон",
        "bio": "Биоотходы",
        "garden": "Садовые отходы",
        "bulky": "Крупногабаритные отходы",
        "hazardous": "Опасные отходы",
        "mixed": "Смешанные отходы",
    },
}


def waste_category(waste_name: str) -> str | None:
    """Return the category key for a provider waste name, or None if unknown."""
    name = waste_name.casefold()
    for key, patterns in WASTE_CATEGORIES:
        if any(pattern in name for pattern in patterns):
            return key
    return None


def display_name(waste_name: str, language: str) -> str:
    """Return a localised name for a waste type, falling back to the provider's name."""
    category = waste_category(waste_name)
    if category is None:
        return waste_name
    names = CATEGORY_NAMES.get(language.split("-")[0], CATEGORY_NAMES["en"])
    return names[category]
