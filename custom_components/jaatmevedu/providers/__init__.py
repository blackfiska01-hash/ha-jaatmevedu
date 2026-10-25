"""Waste carriers with a public schedule lookup."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp

from ..const import (
    CONF_ADDRESS,
    CONF_AREA,
    CONF_CLIENT_CODE,
    CONF_CONTRACT_NUMBER,
    CONF_PROVIDER,
    CONF_UNIT,
    PROVIDER_EKT,
    PROVIDER_RAGNSELLS,
    PROVIDER_TJT,
)
from .base import AddressMatch, Collection, NotFoundError, Provider, ProviderError
from .ekt import EktProvider
from .ragnsells import RagnSellsProvider
from .tjt import TjtProvider

__all__ = [
    "AddressMatch",
    "Collection",
    "NotFoundError",
    "Provider",
    "ProviderError",
    "create_provider",
]


def create_provider(session: aiohttp.ClientSession, data: Mapping[str, Any]) -> Provider:
    """Build the provider described by a config entry's data."""
    kind = data.get(CONF_PROVIDER, PROVIDER_EKT)
    if kind == PROVIDER_RAGNSELLS:
        return RagnSellsProvider(
            session,
            data[CONF_AREA],
            address=data.get(CONF_ADDRESS, ""),
            unit=data.get(CONF_UNIT, ""),
            client_code=data.get(CONF_CLIENT_CODE, ""),
        )
    if kind == PROVIDER_TJT:
        return TjtProvider(session, data[CONF_ADDRESS])
    return EktProvider(session, data[CONF_CONTRACT_NUMBER])
