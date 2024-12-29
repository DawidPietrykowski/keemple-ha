"""The Keemple integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_COUNTRY_CODE
from .coordinator import KeempleDataUpdateCoordinator
from .api import KeempleHome

PLATFORMS: list[Platform] = [Platform.LIGHT]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Keemple from a config entry."""
    api = KeempleHome(
        hass=hass,  # Pass hass instance
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        country_code=entry.data.get(CONF_COUNTRY_CODE, "0")
    )
    coordinator = KeempleDataUpdateCoordinator(hass, api)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
