"""Tallinna Jäätmete Taaskasutuskeskus AS: public schedule by address.

TJT publishes schedules only for some areas (currently Saku vald); its Tallinn
districts are behind an ID-card login.
"""

from __future__ import annotations

from typing import Any

import aiohttp

from .base import (
    AddressMatch,
    Collection,
    NotFoundError,
    Provider,
    ProviderError,
    async_request,
    dedupe_sorted,
    parse_ee_date,
    parse_frequency,
    parse_weekdays,
)

BASE_URL = "https://tjt.ee/wp-json/tjt/v1/schedule/search"
LOOKUP_URL = "https://tjt.ee/jaatmeveo-graafik/"
AREAS = ["Saku vald"]


async def _query(
    session: aiohttp.ClientSession, path: str, params: dict[str, str]
) -> dict[str, Any]:
    payload = await async_request(session, f"{BASE_URL}/{path}", params, json=True)
    if not isinstance(payload, dict):
        raise ProviderError("Unexpected response type")
    return payload


async def async_search(
    session: aiohttp.ClientSession, area: str, address: str
) -> list[AddressMatch]:
    """Full addresses in an area matching a search string."""
    payload = await _query(session, "address", {"address": address, "area": area})
    return [AddressMatch(r) for r in payload.get("results") or [] if isinstance(r, str)]


def parse(payload: dict[str, Any]) -> list[Collection]:
    results = payload.get("results")
    if not isinstance(results, dict):
        return []
    address = str(results.get("address") or "")
    collections = []
    for row in results.get("rows") or []:
        if not isinstance(row, list) or len(row) < 4:
            continue
        frequency, day, waste_type, raw_date = (str(v) for v in row[:4])
        when = parse_ee_date(raw_date)
        if when is None or not waste_type:
            continue
        collections.append(
            Collection(
                date=when,
                waste_type=waste_type,
                address=address,
                frequency_days=parse_frequency(frequency),
                weekdays=parse_weekdays(day),
            )
        )
    return dedupe_sorted(collections)


class TjtProvider(Provider):
    """About a month of collection days for one address."""

    def __init__(self, session: aiohttp.ClientSession, address: str) -> None:
        super().__init__(session)
        self.address = address

    async def async_fetch(self) -> list[Collection]:
        payload = await _query(self._session, "schedule", {"address": self.address})
        collections = parse(payload)
        if not collections and payload.get("messages"):
            raise NotFoundError(self.address)
        return collections
