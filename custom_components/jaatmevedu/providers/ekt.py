"""Eesti Keskkonnateenused AS: public next-collection lookup by contract number."""

from __future__ import annotations

from typing import Any

import aiohttp

from .base import (
    Collection,
    NotFoundError,
    Provider,
    ProviderError,
    async_request,
    dedupe_sorted,
    parse_ee_date,
)

API_URL = "https://cms.keskkonnateenused.ee/wp-json/general-purpose-api/upcoming-discharges"
LOOKUP_URL = "https://www.keskkonnateenused.ee/klienditugi/j%C3%A4rgmine-veop%C3%A4ev"


class EktProvider(Provider):
    """The carrier publishes only the next collection day per container."""

    def __init__(self, session: aiohttp.ClientSession, contract_number: str) -> None:
        super().__init__(session)
        self.contract_number = contract_number

    async def async_fetch(self) -> list[Collection]:
        payload = await async_request(
            self._session, API_URL, {"contractNumber": self.contract_number}, json=True
        )
        # Unknown contracts come back as HTTP 200 with {"statusCode": 404, ...}.
        if isinstance(payload, dict):
            if payload.get("statusCode") == 404:
                raise NotFoundError(self.contract_number)
            raise ProviderError(f"Unexpected response: {payload.get('message', payload)}")
        if not isinstance(payload, list):
            raise ProviderError("Unexpected response type")
        return parse(payload)


def parse(items: list[Any]) -> list[Collection]:
    """Turn API rows into collections, skipping malformed rows."""
    result: list[Collection] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        when = parse_ee_date(str(item.get("date") or ""))
        container = str(item.get("itemType") or "").strip()
        waste_type = str(item.get("garbage") or "").strip() or container
        if when is None or not waste_type:
            continue
        result.append(
            Collection(
                date=when,
                waste_type=waste_type,
                address=str(item.get("address") or "").strip(),
                container=container,
            )
        )
    return dedupe_sorted(result)
