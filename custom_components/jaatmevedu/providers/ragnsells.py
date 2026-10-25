"""Ragn-Sells AS: public schedule table by area plus address or client code.

Ragn-Sells limits its public table for data-protection reasons, so not every
address is listed; searching by client code (kliendikood) reaches the rest.
"""

from __future__ import annotations

from html.parser import HTMLParser

import aiohttp

from .base import (
    AddressMatch,
    Collection,
    NotFoundError,
    Provider,
    async_request,
    dedupe_sorted,
    parse_ee_date,
    parse_frequency,
    parse_weekdays,
)

URL = "https://api.ragnsells.ee/graafikud/"
LOOKUP_URL = "https://www.ragnsells.ee/klienditugi/kliendile/graafikud"
# The form's text inputs accept at most 20 characters.
MAX_QUERY = 20


class _Page(HTMLParser):
    """Collects the area <select> options and the result table rows."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.areas: dict[str, str] = {}
        self.rows: list[list[str]] = []
        self._select: str | None = None
        self._option: str | None = None
        self._in_tbody = False
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "select":
            self._select = dict(attrs).get("name")
        elif tag == "option" and self._select == "piirkond":
            self._option = dict(attrs).get("value") or ""
            self.areas[self._option] = ""
        elif tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self._select = None
        elif tag == "option":
            self._option = None
        elif tag == "tbody":
            self._in_tbody = False
        elif tag == "td" and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._option is not None:
            self.areas[self._option] += data.strip()
        elif self._cell is not None:
            self._cell.append(data)


def parse_page(html: str) -> _Page:
    page = _Page()
    page.feed(html)
    return page


def rows_to_collections(rows: list[list[str]]) -> list[Collection]:
    result = []
    for row in rows:
        if len(row) < 6:
            continue
        address, unit, frequency, days, waste_type, raw_date = row[:6]
        when = parse_ee_date(raw_date)
        if when is None or not waste_type:
            continue
        result.append(
            Collection(
                date=when,
                waste_type=waste_type,
                address=f"{address}, {unit}" if unit else address,
                frequency_days=parse_frequency(frequency),
                weekdays=parse_weekdays(days),
            )
        )
    return dedupe_sorted(result)


async def _query(session: aiohttp.ClientSession, params: dict[str, str]) -> _Page:
    full = {"addr": "", "kl_kood": "", "teenuse_tyyp": "", **params}
    html: str = await async_request(session, URL, full, json=False)
    return parse_page(html)


async def async_get_areas(session: aiohttp.ClientSession) -> dict[str, str]:
    """The carrier's areas as {id: name}."""
    page = await _query(session, {})
    return {k: v for k, v in page.areas.items() if k and v}


async def async_search(
    session: aiohttp.ClientSession, area: str, address: str
) -> list[AddressMatch]:
    """Addresses in an area that start like the query."""
    page = await _query(session, {"piirkond": area, "addr": address[:MAX_QUERY]})
    seen: dict[tuple[str, str], AddressMatch] = {}
    for row in page.rows:
        if len(row) >= 2:
            seen.setdefault((row[0], row[1]), AddressMatch(row[0], row[1]))
    return sorted(seen.values(), key=lambda m: m.label)


class RagnSellsProvider(Provider):
    """Schedules for one address, or for everything under one client code."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        area: str,
        *,
        address: str = "",
        unit: str = "",
        client_code: str = "",
    ) -> None:
        super().__init__(session)
        self.area = area
        self.address = address
        self.unit = unit
        self.client_code = client_code

    async def async_fetch(self) -> list[Collection]:
        params = {"piirkond": self.area}
        if self.client_code:
            params["kl_kood"] = self.client_code[:MAX_QUERY]
        else:
            params["addr"] = self.address[:MAX_QUERY]
        rows = (await _query(self._session, params)).rows
        if not self.client_code:
            rows = [r for r in rows if len(r) >= 2 and r[0] == self.address and r[1] == self.unit]
        if not rows:
            raise NotFoundError(self.client_code or self.address)
        return rows_to_collections(rows)
