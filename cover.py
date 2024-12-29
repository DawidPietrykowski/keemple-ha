"""Support for Keemple covers."""
import logging
from typing import Any, Optional

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    ATTR_POSITION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    DEVICE_TYPE_BLIND,
    BLIND_MIN_POSITION,
    BLIND_MAX_POSITION,
    HA_MAX_POSITION
)
from .coordinator import KeempleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Keemple covers."""
    coordinator: KeempleDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    covers = []
    for device in coordinator.api.get_devices_by_type(DEVICE_TYPE_BLIND):
        covers.append(KeempleCover(coordinator, device))
    
    async_add_entities(covers)

class KeempleCover(CoverEntity):
    """Representation of a Keemple Cover."""

    def __init__(self, coordinator: KeempleDataUpdateCoordinator, device):
        """Initialize the cover."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = device.unique_id
        self._attr_name = device.name
        self._attr_device_info = device.device_info
        
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.STOP
        )

    def _keemple_to_ha_position(self, position: int) -> int:
        """Convert Keemple position (0-99) to Home Assistant position (0-100)."""
        if position >= BLIND_MAX_POSITION:
            return HA_MAX_POSITION
        return round((position / BLIND_MAX_POSITION) * HA_MAX_POSITION)

    def _ha_to_keemple_position(self, position: int) -> int:
        """Convert Home Assistant position (0-100) to Keemple position (0-99)."""
        if position >= HA_MAX_POSITION:
            return BLIND_MAX_POSITION
        return round((position / HA_MAX_POSITION) * BLIND_MAX_POSITION)

    @property
    def current_cover_position(self) -> int:
        """Return current position of cover."""
        return self._keemple_to_ha_position(self.device.status)

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed."""
        return self.device.status == BLIND_MIN_POSITION

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return False

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return False

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self.async_set_cover_position(position=HA_MAX_POSITION)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self.async_set_cover_position(position=BLIND_MIN_POSITION)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self.coordinator.api.operate_blind(self.device, "stop")
        await self.coordinator.trigger_delayed_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        if position is not None:
            # Convert HA position to Keemple position
            keemple_position = self._ha_to_keemple_position(position)
            
            success = await self.coordinator.api.operate_blind(
                self.device, "open", keemple_position
            )
            if success:
                self.device.status = keemple_position
                self.async_write_ha_state()
                # await self.coordinator.trigger_delayed_refresh()
            else:
                _LOGGER.error("Failed to set position for %s", self.name)
