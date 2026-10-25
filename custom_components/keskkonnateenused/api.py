"""Client for the public Eesti Keskkonnateenused next-collection lookup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import aiohttp

from .const import API_URL

TIMEOUT = aiohttp.ClientTimeout(total=30)
USER_AGENT = (
    "HomeAssistant-Keskkonnateenused (+https://github.com/blackfiska01-hash/ha-keskkonnateenused)"
)


class KeskkonnateenusedError(Exception):
    """The lookup could not be completed."""


class ContractNotFoundError(KeskkonnateenusedError):
    """The provider does not know this contract number."""


@dataclass(frozen=True, slots=True)
class Discharge:
    """One upcoming container emptying."""

    date: date
    waste_type: str
    container: str
    address: str


class KeskkonnateenusedClient:
    """Fetches upcoming collections for one contract."""

    def __init__(self, session: aiohttp.ClientSession, contract_number: str) -> None:
        self._session = session
        self.contract_number = contract_number

    async def async_get_discharges(self) -> list[Discharge]:
        """Return the upcoming collections, one per container."""
        try:
            async with self._session.get(
                API_URL,
                params={"contractNumber": self.contract_number},
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            ) as response:
                response.raise_for_status()
                payload: Any = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise KeskkonnateenusedError(f"Lookup failed: {err}") from err

        # Unknown contracts come back as HTTP 200 with {"statusCode": 404, ...}.
        if isinstance(payload, dict):
            if payload.get("statusCode") == 404:
                raise ContractNotFoundError(self.contract_number)
            raise KeskkonnateenusedError(f"Unexpected response: {payload.get('message', payload)}")
        if not isinstance(payload, list):
            raise KeskkonnateenusedError("Unexpected response type")

        return parse_discharges(payload)


def parse_discharges(items: list[Any]) -> list[Discharge]:
    """Turn the API rows into discharges, skipping malformed rows and duplicates."""
    result: list[Discharge] = []
    seen: set[tuple[date, str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        waste_type = str(item.get("garbage") or "").strip()
        container = str(item.get("itemType") or "").strip()
        raw_date = str(item.get("date") or "")[:10]
        try:
            when = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if not waste_type:
            waste_type = container
        if not waste_type:
            continue
        key = (when, waste_type, container)
        if key in seen:
            continue
        seen.add(key)
        result.append(
            Discharge(
                date=when,
                waste_type=waste_type,
                container=container,
                address=str(item.get("address") or "").strip(),
            )
        )
    result.sort(key=lambda d: (d.date, d.waste_type))
    return result
