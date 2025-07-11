"""DataUpdateCoordinator for Keemple."""
from datetime import timedelta
import logging
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, DEFAULT_REFRESH_DELAY
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

    async def trigger_delayed_refresh(self):
        if DEFAULT_REFRESH_DELAY == 0:
            return
        await asyncio.sleep(DEFAULT_REFRESH_DELAY)
        self.async_request_refresh()

    async def _async_update_data(self):
        """Update data via library."""
        try:
            data = await self.api.async_update_data()
            _LOGGER.debug("Coordinator update successful")  # Add debug logging
            return data
        except Exception as error:
            _LOGGER.error("Error communicating with API: %s", error)
            raise UpdateFailed(f"Error communicating with API: {error}")
