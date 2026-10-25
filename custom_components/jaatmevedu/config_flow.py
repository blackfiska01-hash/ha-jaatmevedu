"""Config flow for Eesti jäätmevedu: pick a carrier, then identify the property."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ADDRESS,
    CONF_AREA,
    CONF_CLIENT_CODE,
    CONF_CONTRACT_NUMBER,
    CONF_PROVIDER,
    CONF_SEARCH,
    CONF_UNIT,
    DOMAIN,
    PROVIDER_EKT,
    PROVIDER_NAMES,
    PROVIDER_RAGNSELLS,
    PROVIDER_TJT,
)
from .providers import (
    AddressMatch,
    Collection,
    NotFoundError,
    ProviderError,
    create_provider,
    ekt,
    ragnsells,
    tjt,
)

_LOGGER = logging.getLogger(__name__)

EKT_SCHEMA = vol.Schema({vol.Required(CONF_CONTRACT_NUMBER): str})
SEP = "\t"


def _compact(value: str) -> str:
    return "".join(value.split())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _select(options: list[SelectOptionDict]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN, sort=False)
    )


class JaatmeveduConfigFlow(ConfigFlow, domain=DOMAIN):
    """Carrier menu, then a contract number or an address search."""

    VERSION = 1

    def __init__(self) -> None:
        self._areas: dict[str, str] = {}
        self._area = ""
        self._matches: list[AddressMatch] = []
        self._provider = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask which company collects the waste."""
        return self.async_show_menu(
            step_id="user", menu_options=[PROVIDER_EKT, PROVIDER_RAGNSELLS, PROVIDER_TJT]
        )

    async def _async_try(self, data: dict[str, Any]) -> tuple[list[Collection] | None, str | None]:
        """Fetch once with the new entry's data; return collections or an error key."""
        provider = create_provider(async_get_clientsession(self.hass), data)
        try:
            return await provider.async_fetch(), None
        except NotFoundError:
            return None, "not_found"
        except ProviderError:
            _LOGGER.debug("Schedule lookup failed", exc_info=True)
            return None, "cannot_connect"

    async def _async_finish(
        self, unique_id: str, data: dict[str, Any], title: str
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=data)

    # Eesti Keskkonnateenused ------------------------------------------------

    async def async_step_ekt(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Contract number for Eesti Keskkonnateenused."""
        errors: dict[str, str] = {}
        if user_input is not None:
            number = _compact(user_input[CONF_CONTRACT_NUMBER])
            if not number.isdigit():
                errors[CONF_CONTRACT_NUMBER] = "invalid_contract"
            else:
                data = {CONF_PROVIDER: PROVIDER_EKT, CONF_CONTRACT_NUMBER: number}
                collections, error = await self._async_try(data)
                if error == "not_found":
                    errors[CONF_CONTRACT_NUMBER] = "contract_not_found"
                elif error:
                    errors["base"] = error
                else:
                    address = next((c.address for c in collections or () if c.address), "")
                    # The contract number alone stays the unique ID, as before the rename.
                    return await self._async_finish(number, data, address or f"Leping {number}")
        return self.async_show_form(
            step_id="ekt",
            data_schema=self.add_suggested_values_to_schema(EKT_SCHEMA, user_input),
            errors=errors,
            description_placeholders={"lookup_url": ekt.LOOKUP_URL},
        )

    # Ragn-Sells -------------------------------------------------------------

    async def async_step_ragnsells(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Area plus an address search or a client code."""
        session = async_get_clientsession(self.hass)
        if not self._areas:
            try:
                self._areas = await ragnsells.async_get_areas(session)
            except ProviderError:
                return self.async_abort(reason="cannot_connect")
            if not self._areas:
                return self.async_abort(reason="cannot_connect")

        errors: dict[str, str] = {}
        if user_input is not None:
            area = user_input[CONF_AREA]
            client_code = _compact(user_input.get(CONF_CLIENT_CODE, ""))
            search = user_input.get(CONF_SEARCH, "").strip()
            if client_code:
                data = {
                    CONF_PROVIDER: PROVIDER_RAGNSELLS,
                    CONF_AREA: area,
                    CONF_CLIENT_CODE: client_code,
                }
                collections, error = await self._async_try(data)
                if error:
                    errors["base" if error == "cannot_connect" else CONF_CLIENT_CODE] = error
                else:
                    address = next((c.address for c in collections or () if c.address), "")
                    return await self._async_finish(
                        f"ragnsells_{area}_{client_code}",
                        data,
                        address or f"Ragn-Sells {client_code}",
                    )
            elif search:
                try:
                    self._matches = await ragnsells.async_search(session, area, search)
                except ProviderError:
                    errors["base"] = "cannot_connect"
                else:
                    if self._matches:
                        self._area, self._provider = area, PROVIDER_RAGNSELLS
                        return await self.async_step_pick()
                    errors[CONF_SEARCH] = "no_results"
            else:
                errors["base"] = "missing_query"

        schema = vol.Schema(
            {
                vol.Required(CONF_AREA): _select(
                    [SelectOptionDict(value=k, label=v) for k, v in self._areas.items()]
                ),
                vol.Optional(CONF_SEARCH): str,
                vol.Optional(CONF_CLIENT_CODE): str,
            }
        )
        return self.async_show_form(
            step_id="ragnsells",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
            description_placeholders={"lookup_url": ragnsells.LOOKUP_URL},
        )

    # TJT --------------------------------------------------------------------

    async def async_step_tjt(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Area plus an address search."""
        errors: dict[str, str] = {}
        if user_input is not None:
            area, search = user_input[CONF_AREA], user_input[CONF_SEARCH].strip()
            try:
                self._matches = await tjt.async_search(
                    async_get_clientsession(self.hass), area, search
                )
            except ProviderError:
                errors["base"] = "cannot_connect"
            else:
                if self._matches:
                    self._area, self._provider = area, PROVIDER_TJT
                    return await self.async_step_pick()
                errors[CONF_SEARCH] = "no_results"

        schema = vol.Schema(
            {
                vol.Required(CONF_AREA, default=tjt.AREAS[0]): _select(
                    [SelectOptionDict(value=a, label=a) for a in tjt.AREAS]
                ),
                vol.Required(CONF_SEARCH): str,
            }
        )
        return self.async_show_form(
            step_id="tjt",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
            description_placeholders={"lookup_url": tjt.LOOKUP_URL},
        )

    # Shared address pick ----------------------------------------------------

    async def async_step_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose one of the addresses the search found."""
        errors: dict[str, str] = {}
        if user_input is not None and CONF_ADDRESS in user_input:
            address, _, unit = user_input[CONF_ADDRESS].partition(SEP)
            data: dict[str, Any] = {
                CONF_PROVIDER: self._provider,
                CONF_AREA: self._area,
                CONF_ADDRESS: address,
            }
            if self._provider == PROVIDER_RAGNSELLS:
                data[CONF_UNIT] = unit
            _, error = await self._async_try(data)
            if error:
                errors["base"] = error
            else:
                label = AddressMatch(address, unit).label
                return await self._async_finish(
                    f"{self._provider}_{_slug(self._area)}_{_slug(label)}", data, label
                )

        options = [
            SelectOptionDict(value=f"{m.address}{SEP}{m.unit}", label=m.label)
            for m in self._matches
        ]
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): _select(options)}),
            errors=errors,
            description_placeholders={"provider": PROVIDER_NAMES[self._provider]},
        )
