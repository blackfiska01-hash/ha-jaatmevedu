"""Constants for the Eesti jäätmevedu integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "jaatmevedu"

CONF_CONTRACT_NUMBER: Final = "contract_number"

CONF_PROVIDER: Final = "provider"
CONF_AREA: Final = "area"
CONF_ADDRESS: Final = "address"
CONF_UNIT: Final = "unit"
CONF_CLIENT_CODE: Final = "client_code"
CONF_SEARCH: Final = "search"

PROVIDER_EKT: Final = "ekt"
PROVIDER_RAGNSELLS: Final = "ragnsells"
PROVIDER_TJT: Final = "tjt"

# Carrier names double as device names, so EKT entity IDs keep the
# "eesti_keskkonnateenused_" prefix they had before the rename.
PROVIDER_NAMES: Final[dict[str, str]] = {
    PROVIDER_EKT: "Eesti Keskkonnateenused",
    PROVIDER_RAGNSELLS: "Ragn-Sells",
    PROVIDER_TJT: "TJT",
}
PROVIDER_URLS: Final[dict[str, str]] = {
    PROVIDER_EKT: "https://eteenindus.keskkonnateenused.ee/",
    PROVIDER_RAGNSELLS: "https://www.ragnsells.ee/iseteenindus",
    PROVIDER_TJT: "https://iseteenindus.tjt.ee/",
}
PROVIDER_MANUFACTURERS: Final[dict[str, str]] = {
    PROVIDER_EKT: "Eesti Keskkonnateenused AS",
    PROVIDER_RAGNSELLS: "Ragn-Sells AS",
    PROVIDER_TJT: "Tallinna Jäätmete Taaskasutuskeskus AS",
}

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
    ("mixed", ("sega", "olme")),  # segaolmejäätmed, olmejäätmed
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
