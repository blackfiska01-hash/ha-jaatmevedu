"""Config flow for Eesti Keskkonnateenused."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ContractNotFoundError, Discharge, KeskkonnateenusedClient, KeskkonnateenusedError
from .const import CONF_CONTRACT_NUMBER, DOMAIN, LOOKUP_URL

_LOGGER = logging.getLogger(__name__)

SCHEMA = vol.Schema({vol.Required(CONF_CONTRACT_NUMBER): str})


def _normalise(contract_number: str) -> str:
    return "".join(contract_number.split())


class KeskkonnateenusedConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the contract number and check it against the provider."""

    VERSION = 1

    async def _async_validate(
        self, user_input: dict[str, Any]
    ) -> tuple[str, list[Discharge] | None, dict[str, str]]:
        contract_number = _normalise(user_input[CONF_CONTRACT_NUMBER])
        errors: dict[str, str] = {}
        discharges: list[Discharge] | None = None
        if not contract_number.isdigit():
            errors[CONF_CONTRACT_NUMBER] = "invalid_contract"
            return contract_number, None, errors
        client = KeskkonnateenusedClient(async_get_clientsession(self.hass), contract_number)
        try:
            discharges = await client.async_get_discharges()
        except ContractNotFoundError:
            errors[CONF_CONTRACT_NUMBER] = "contract_not_found"
        except KeskkonnateenusedError:
            _LOGGER.debug("Contract lookup failed", exc_info=True)
            errors["base"] = "cannot_connect"
        return contract_number, discharges, errors

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            contract_number, discharges, errors = await self._async_validate(user_input)
            if not errors:
                await self.async_set_unique_id(contract_number)
                self._abort_if_unique_id_configured()
                address = next((d.address for d in discharges or () if d.address), "")
                return self.async_create_entry(
                    title=address or f"Leping {contract_number}",
                    data={CONF_CONTRACT_NUMBER: contract_number},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input),
            errors=errors,
            description_placeholders={"lookup_url": LOOKUP_URL},
        )
