"""Shared types for waste carrier providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=30)
USER_AGENT = "HomeAssistant-Jaatmevedu (+https://github.com/blackfiska01-hash/ha-jaatmevedu)"


class ProviderError(Exception):
    """The carrier could not be queried."""


class NotFoundError(ProviderError):
    """The carrier does not know this contract, address or client code."""


WEEKDAYS = {"E": "mon", "T": "tue", "K": "wed", "N": "thu", "R": "fri", "L": "sat", "P": "sun"}


@dataclass(frozen=True, slots=True)
class Collection:
    """One upcoming container emptying."""

    date: date
    waste_type: str
    address: str
    container: str = ""
    frequency_days: int | None = None
    weekdays: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AddressMatch:
    """An address offered by a carrier's search."""

    address: str
    unit: str = ""

    @property
    def label(self) -> str:
        return f"{self.address}, {self.unit}" if self.unit else self.address


class Provider(ABC):
    """A carrier's public schedule lookup."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    @abstractmethod
    async def async_fetch(self) -> list[Collection]:
        """Return upcoming collections, sorted by date."""


async def async_request(
    session: aiohttp.ClientSession, url: str, params: dict[str, str], *, json: bool
) -> Any:
    """GET a carrier endpoint, mapping transport and decoding errors to ProviderError."""
    try:
        async with session.get(
            url,
            params=params,
            headers={
                "Accept": "application/json" if json else "text/html",
                "User-Agent": USER_AGENT,
            },
            timeout=TIMEOUT,
        ) as response:
            response.raise_for_status()
            if json:
                return await response.json(content_type=None)
            return await response.text()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise ProviderError(f"Lookup failed: {err}") from err


def dedupe_sorted(items: list[Collection]) -> list[Collection]:
    """Drop exact duplicates (one row per container) and sort by date."""
    return sorted(set(items), key=lambda c: (c.date, c.waste_type, c.container))


def parse_weekdays(text: str) -> tuple[str, ...]:
    """Estonian weekday letters ("E, K, R") to ("mon", "wed", "fri")."""
    return tuple(WEEKDAYS[d] for d in (p.strip() for p in text.split(",")) if d in WEEKDAYS)


def parse_frequency(text: str) -> int | None:
    """Collection interval in days, or None for irregular ("erisagedus")."""
    text = text.strip()
    return int(text) if text.isdigit() else None


def parse_ee_date(text: str) -> date | None:
    """Parse DD.MM.YYYY or YYYY-MM-DD."""
    text = text.strip()[:10]
    try:
        if len(text) == 10 and text[2] == "." and text[5] == ".":
            return date(int(text[6:10]), int(text[3:5]), int(text[0:2]))
        return date.fromisoformat(text)
    except ValueError:
        return None
