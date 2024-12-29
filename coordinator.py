"""DataUpdateCoordinator for Keemple."""
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .api import KeempleHome

_LOGGER = logging.getLogger(__name__)

class KeempleDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Keemple data."""

    def __init__(self, hass: HomeAssistant, api: KeempleHome) -> None:
        """Initialize."""
        self.api = api

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.async_update_data()
        except Exception as error:
            raise UpdateFailed(f"Error communicating with API: {error}")
