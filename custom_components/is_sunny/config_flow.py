"""UI configuration flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AZIMUTH, CONF_CLOUD, CONF_ELEVATION, CONF_LUX, CONF_PV,
    CONF_TEMPERATURE, CONF_ON_THRESHOLD, CONF_OFF_THRESHOLD,
    CONF_MIN_ELEVATION, CONF_MIN_SAMPLES, DEFAULTS, DOMAIN,
)


def _entity(key: str, domain: str = "sensor") -> vol.Marker:
    return vol.Required(key, default=DEFAULTS[key])


SCHEMA = vol.Schema({
    _entity(CONF_PV): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
    _entity(CONF_AZIMUTH): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
    _entity(CONF_ELEVATION): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
    _entity(CONF_LUX): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
    _entity(CONF_CLOUD): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
    _entity(CONF_TEMPERATURE): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
})


class IsSunnyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Is Sunny", data=user_input)
        return self.async_show_form(step_id="user", data_schema=SCHEMA)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return IsSunnyOptionsFlow(config_entry)


class IsSunnyOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = DEFAULTS | self.entry.options
        schema = vol.Schema({
            vol.Required(CONF_ON_THRESHOLD, default=current[CONF_ON_THRESHOLD]):
                vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1.5)),
            vol.Required(CONF_OFF_THRESHOLD, default=current[CONF_OFF_THRESHOLD]):
                vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1.5)),
            vol.Required(CONF_MIN_ELEVATION, default=current[CONF_MIN_ELEVATION]):
                vol.All(vol.Coerce(float), vol.Range(min=-5, max=45)),
            vol.Required(CONF_MIN_SAMPLES, default=current[CONF_MIN_SAMPLES]):
                vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
