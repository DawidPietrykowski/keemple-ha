"""Support for Keemple climate devices."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    DEVICE_TYPE_HEATER,
    HEATER_MIN_TEMP,
    HEATER_MAX_TEMP,
    HEATER_STEP,
    TEMP_TARGET_IDX,
    TEMP_CURRENT_IDX,
    POWER_STATE_IDX,
)
from .coordinator import KeempleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Keemple climate devices."""
    coordinator: KeempleDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    climate_devices = []
    for device in coordinator.api.get_devices_by_type(DEVICE_TYPE_HEATER):
        climate_devices.append(KeempleClimate(coordinator, device))
    
    async_add_entities(climate_devices)

class KeempleClimate(ClimateEntity):
    """Representation of a Keemple Climate device."""

    def __init__(self, coordinator: KeempleDataUpdateCoordinator, device):
        """Initialize the climate device."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = device.unique_id
        self._attr_name = device.name
        self._attr_device_info = device.device_info
        
        # Set supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
        )
        
        # Set temperature settings
        self._attr_min_temp = HEATER_MIN_TEMP
        self._attr_max_temp = HEATER_MAX_TEMP
        self._attr_target_temperature_step = HEATER_STEP
        
        # Set temperature unit
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        
        # Set supported HVAC modes
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        try:
            states = self.device.statuses
            if states and len(states) > TEMP_CURRENT_IDX:
                return float(states[TEMP_CURRENT_IDX])
        except (ValueError, TypeError):
            pass
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        try:
            states = self.device.statuses
            if states and len(states) > TEMP_TARGET_IDX:
                return float(states[TEMP_TARGET_IDX])
        except (ValueError, TypeError):
            pass
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        try:
            states = self.device.statuses
            if states and len(states) > POWER_STATE_IDX:
                return HVACMode.HEAT if int(states[POWER_STATE_IDX]) else HVACMode.OFF
        except (ValueError, TypeError):
            pass
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        
        current = self.current_temperature
        target = self.target_temperature
        
        if current is None or target is None:
            return None
            
        if current < target:
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            success = await self.coordinator.api.set_heater_temperature(
                self.device, temperature
            )
            if success:
                # Update the local state
                if self.device.statuses:
                    self.device.statuses[TEMP_TARGET_IDX] = temperature
                self.async_write_ha_state()
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to set temperature for %s", self.name)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        power = 255 if hvac_mode == HVACMode.HEAT else 0
        
        success = await self.coordinator.api.set_heater_power(
            self.device, power
        )
        if success:
            # Update the local state
            if self.device.statuses:
                self.device.statuses[POWER_STATE_IDX] = 1 if power else 0
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set mode for %s", self.name)

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        return self.device.battery

    async def async_update(self) -> None:
        """Update the entity."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
