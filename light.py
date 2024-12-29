"""Support for Keemple lights."""
import logging
from typing import Any

from homeassistant.components.light import LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DEVICE_TYPE_LIGHT, DEVICE_TYPE_LIGHT_DUAL
from .coordinator import KeempleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Keemple lights."""
    coordinator: KeempleDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    lights = []
    # Add both single and dual light types
    for device in coordinator.api.get_devices_by_type(DEVICE_TYPE_LIGHT):
        lights.append(KeempleLight(coordinator, device))
    for device in coordinator.api.get_devices_by_type(DEVICE_TYPE_LIGHT_DUAL):
        lights.append(KeempleLight(coordinator, device))
    
    async_add_entities(lights)

class KeempleLight(LightEntity):
    """Representation of a Keemple Light."""

    def __init__(self, coordinator: KeempleDataUpdateCoordinator, device):
        """Initialize the light."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = device.unique_id
        self._attr_name = device.display_name
        self._attr_device_info = device.device_info

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.device.status == 1

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        success = await self.coordinator.api.turn_on(self.device)
        if success:
            self.device.status = 1
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn on %s", self.name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        success = await self.coordinator.api.turn_off(self.device)
        if success:
            self.device.status = 0
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn off %s", self.name)

    async def async_update(self) -> None:
        """Update the entity."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
