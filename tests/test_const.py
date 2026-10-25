"""Tests for waste type classification."""

from __future__ import annotations

import pytest

from custom_components.keskkonnateenused.const import display_name, waste_category


@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Segaolmejäätmed", "mixed"),
        ("Segapakendid", "packaging"),
        ("Klaaspakend", "glass"),
        ("Paber ja kartong", "paper"),
        ("Biolagunevad köögi- ja sööklajäätmed", "bio"),
        ("Aia- ja haljastusjäätmed", "garden"),
        ("Suurjäätmed", "bulky"),
        ("Ohtlikud jäätmed", "hazardous"),
        ("Midagi muud", None),
    ],
)
def test_category(name: str, category: str | None) -> None:
    assert waste_category(name) == category


def test_display_name() -> None:
    assert display_name("Segaolmejäätmed", "ru") == "Смешанные отходы"
    assert display_name("Segaolmejäätmed", "en-GB") == "Mixed waste"
    assert display_name("Segaolmejäätmed", "fi") == "Mixed waste"
    assert display_name("Midagi muud", "ru") == "Midagi muud"
