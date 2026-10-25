"""Shared fixtures for the Eesti jäätmevedu tests."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.jaatmevedu.const import (
    CONF_CONTRACT_NUMBER,
    CONF_PROVIDER,
    DOMAIN,
    PROVIDER_EKT,
)
from custom_components.jaatmevedu.providers import ekt

pytest_plugins = ["pytest_homeassistant_custom_component"]

CONTRACT = "1234567"
ADDRESS = "Näidise tn 1, Tallinn, Harju maakond"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom_components/ in every test."""


def ekt_rows(*items: tuple[str, str, str]) -> list[dict[str, Any]]:
    """EKT API rows from (date, garbage, itemType) tuples."""
    return [
        {"address": ADDRESS, "contractNumber": CONTRACT, "date": d, "garbage": g, "itemType": t}
        for d, g, t in items
    ]


DEFAULT_ROWS = ekt_rows(
    ("2026-10-28", "Segaolmejäätmed", "0,24 m3 plastikkonteiner"),
    ("2026-11-04", "Segapakendid", "0,24 m3 plastikkonteiner"),
)

RS_AREAS = {"463": "Kose vald", "521": "Pärnu linn 1 piirkond"}


def rs_page(rows: list[tuple[str, ...]] = (), *, not_found: bool = False) -> str:
    """A Ragn-Sells schedule page with the given result rows."""
    options = "".join(f'<option value="{k}">{v}</option>' for k, v in RS_AREAS.items())
    body = "".join(
        '<tr valign="top">' + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows
    )
    table = (
        '<table class="graafikud_tabel"><thead><tr><th>Aadress</th><th>Haldusüksus</th>'
        "<th>Sagedus</th><th>Päev</th><th>Teenuse tüüp</th><th>Järgmine tühjendus kp.</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
        if rows
        else ""
    )
    message = "Ei leitud ühtegi sarnast aadressi!" if not_found else ""
    return (
        '<html><body><form class="contract_form"><select name="piirkond">'
        f'{options}</select><input name="addr"><select name="teenuse_tyyp">'
        '<option value=""></option><option value="10">Olmejäätmed</option></select>'
        f"</form>{table}{message}</body></html>"
    )


RS_ROWS = [
    (
        "Kose mnt 19",
        "Habaja alevik, Kose, Harju maakond",
        "14",
        "E",
        "Biolagunevad jäätmed",
        "02.11.2026",
    ),
    (
        "Kose mnt 19",
        "Habaja alevik, Kose, Harju maakond",
        "28",
        "N, E",
        "Olmejäätmed",
        "29.10.2026",
    ),
    (
        "Kose mnt 19",
        "Habaja alevik, Kose, Harju maakond",
        "28",
        "N, E",
        "Olmejäätmed",
        "29.10.2026",
    ),
    ("Kose mnt 3a", "Habaja alevik, Kose, Harju maakond", "28", "K", "Segapakend", "18.11.2026"),
]

TJT_ADDRESS = "Harju maakond, Saku vald, Saku alevik, Näidise tee 4"
TJT_SCHEDULE = {
    "messages": [],
    "results": {
        "address": TJT_ADDRESS,
        "unit": "Saku alevik",
        "headers": [
            "Address",
            "Haldusüksus",
            "Sagedus",
            "Päev",
            "Teenuse tüüp",
            "Tühjendamise päev",
        ],
        "rows": [
            ["erisagedus", "E", "Segaolmejäätmed", "26.10.2026"],
            ["erisagedus", "E", "Segaolmejäätmed", "26.10.2026"],
            ["14", "K", "Biojäätmed", "28.10.2026"],
            ["erisagedus", "K", "Segaolmejäätmed", "28.10.2026"],
            ["14", "K", "Biojäätmed", "11.11.2026"],
        ],
        "types": {},
    },
}


@pytest.fixture
def api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Answer the EKT lookup with two upcoming collections."""
    aioclient_mock.get(ekt.API_URL, json=DEFAULT_ROWS)
    return aioclient_mock


@pytest.fixture
def entry() -> MockConfigEntry:
    """An EKT config entry for the test contract."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=ADDRESS,
        unique_id=CONTRACT,
        data={CONF_PROVIDER: PROVIDER_EKT, CONF_CONTRACT_NUMBER: CONTRACT},
    )
