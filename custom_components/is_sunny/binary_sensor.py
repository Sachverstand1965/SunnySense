"""Binary sensor platform."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from . import RuntimeData
from .const import (
    CONF_AZIMUTH, CONF_CLOUD, CONF_ELEVATION, CONF_LUX, CONF_MIN_ELEVATION,
    CONF_MIN_SAMPLES, CONF_OFF_THRESHOLD, CONF_ON_THRESHOLD, CONF_PV,
    CONF_TEMPERATURE, DEFAULTS,
)
from .model import active_facade, learning_allowed


def _number(hass: HomeAssistant, entity_id: str) -> float | None:
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable"):
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([IsSunnyBinarySensor(hass, entry)])


class IsSunnyBinarySensor(RestoreEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Is Sunny"
    _attr_icon = "mdi:white-balance-sunny"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.runtime: RuntimeData = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_is_sunny"
        self._attr_is_on: bool | None = None
        self._attrs: dict[str, Any] = {}
        self._last_saved = None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        if previous and previous.state in ("on", "off"):
            self._attr_is_on = previous.state == "on"
        entities = [self.entry.data[key] for key in (
            CONF_PV, CONF_AZIMUTH, CONF_ELEVATION, CONF_LUX, CONF_CLOUD,
            CONF_TEMPERATURE,
        )]
        self.async_on_remove(async_track_state_change_event(self.hass, entities, self._changed))
        self._evaluate()

    @callback
    def _changed(self, event: Event[EventStateChangedData]) -> None:
        self._evaluate()
        self.async_write_ha_state()

    def _evaluate(self) -> None:
        data = self.entry.data | self.entry.options
        pv = _number(self.hass, data[CONF_PV])
        az = _number(self.hass, data[CONF_AZIMUTH])
        el = _number(self.hass, data[CONF_ELEVATION])
        lux = _number(self.hass, data[CONF_LUX])
        cloud = _number(self.hass, data[CONF_CLOUD])
        temp = _number(self.hass, data[CONF_TEMPERATURE])
        if pv is None or az is None or el is None:
            self._attr_is_on = None
            self._attrs = {"reason": "required_input_unavailable"}
            return
        facade = active_facade(az)
        min_el = float(data.get(CONF_MIN_ELEVATION, DEFAULTS[CONF_MIN_ELEVATION]))
        if facade is None or el < min_el:
            self._attr_is_on = False
            self._attrs = {"reason": "no_facade_illuminated", "azimuth": az, "elevation": el}
            return
        estimate = self.runtime.model.estimate(facade["name"], az, el)
        learning = learning_allowed(elevation=el, pv=pv, lux=lux, cloud=cloud, temperature=temp)
        if learning:
            self.runtime.model.learn(facade["name"], az, el, pv)
            self._schedule_save()
            estimate = self.runtime.model.estimate(facade["name"], az, el)
        minimum = int(data.get(CONF_MIN_SAMPLES, DEFAULTS[CONF_MIN_SAMPLES]))
        ratio = pv / estimate.expected if estimate.expected and estimate.expected > 0 else None
        clearly_cloudy = (
            ratio is not None and cloud is not None and cloud >= 70
            and lux is not None and lux < 20_000
        )
        if ratio is not None and (learning or clearly_cloudy):
            self.runtime.model.adapt_thresholds(facade["name"], ratio, learning)
            self._schedule_save()
        adaptive = self.runtime.model.thresholds[facade["name"]]
        if ratio is None or estimate.samples < minimum:
            self._attr_is_on = None
            reason = "learning_reference_curve"
        else:
            key = CONF_OFF_THRESHOLD if self._attr_is_on else CONF_ON_THRESHOLD
            threshold = float(self.entry.options.get(
                key, adaptive["off" if self._attr_is_on else "on"]
            ))
            self._attr_is_on = ratio >= threshold
            reason = "hysteresis_decision"
        self._attrs = {
            "reason": reason, "active_facade": facade["name"],
            "facade_bearing": facade["bearing"], "azimuth": round(az, 1),
            "elevation": round(el, 1), "pv_power": round(pv, 1),
            "expected_power": round(estimate.expected, 1) if estimate.expected else None,
            "pv_ratio": round(ratio, 3) if ratio is not None else None,
            "sunny_score": round(ratio, 3) if ratio is not None else None,
            "confidence": round(estimate.confidence, 3), "reference_samples": estimate.samples,
            "learning": learning, "lux": lux, "cloud_cover": cloud,
            "temperature": temp,
            "threshold_on": round(self.entry.options.get(CONF_ON_THRESHOLD, adaptive["on"]), 3),
            "threshold_off": round(self.entry.options.get(CONF_OFF_THRESHOLD, adaptive["off"]), 3),
            "threshold_mode": "manual" if CONF_ON_THRESHOLD in self.entry.options else "adaptive",
        }

    def _schedule_save(self) -> None:
        """Coalesce writes through Store's delayed-save mechanism."""
        self.runtime.store.async_delay_save(self.runtime.model.as_dict, timedelta(minutes=5).total_seconds())
