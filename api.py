"""Keemple API Client."""
import logging
import requests
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from homeassistant.core import HomeAssistant
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    BASE_URL,
    DEFAULT_PLATFORM
)

_LOGGER = logging.getLogger(__name__)

@dataclass
class Device:
    """Keemple device representation."""
    name: str
    device_id: str
    device_type: str
    status: int
    nuid: int
    battery: int
    last_active_time: str
    zwavedeviceid: int
    statuses: Optional[str] = None
    
    @property
    def unique_id(self) -> str:
        """Return unique ID for Home Assistant."""
        return f"{DOMAIN}_{self.device_type}_{self.nuid}"
    
    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device info for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Keemple",
            "model": f"Type {self.device_type}",
            "sw_version": None,
        }

class KeempleHome:
    """Keemple API client."""

    def __init__(self, hass: HomeAssistant, username: str, password: str, country_code: str = "0"):
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.country_code = country_code
        self.session = requests.Session()
        self.devices: List[Device] = []
        self.rooms: Dict[str, List[Device]] = {"Unassigned": []}
        self._authenticated = False
        self.raw_data = {}
        self.hass = hass  # Add this line

    async def async_login(self) -> bool:
        """Login to Keemple."""
        params = {
            "platform": DEFAULT_PLATFORM,
            "phonenumber": self.username,
            "countrycode": self.country_code,
            "password": self.password,
            "language": "en_US"
        }
        
        try:
            response = await self._async_request(
                "post",
                f"{BASE_URL}/phoneuser/login",
                params=params
            )
            
            if response.get("resultCode") == 0:
                self._authenticated = True
                return True
            
            _LOGGER.error("Login failed: %s", response.get("resultMessage"))
            return False
            
        except Exception as err:
            _LOGGER.error("Login error: %s", str(err))
            return False

    async def async_update_data(self) -> Dict[str, Any]:
        """Update device data from API."""
        if not self._authenticated:
            await self.async_login()

        params = {
            "platform": DEFAULT_PLATFORM,
        }
        
        try:
            data = await self._async_request(
                "post",
                f"{BASE_URL}/data/querychangeddata2",
                params=params
            )
            
            if data:
                self._parse_devices(data)
                self._organize_rooms()
                self._find_unassigned_devices()
                return data
            
            return {}
            
        except Exception as err:
            _LOGGER.error("Update error: %s", str(err))
            return {}

    async def turn_on(self, device: Device) -> bool:
        """Turn on a device."""
        return await self.async_operate_device(device, "open")

    async def turn_off(self, device: Device) -> bool:
        """Turn off a device."""
        return await self.async_operate_device(device, "close")

    async def async_operate_device(self, device: Device, operation: str) -> bool:
        """Operate a device (turn on/off)."""
        if not self._authenticated:
            await self.async_login()

        params = {
            "platform": DEFAULT_PLATFORM,
            "zwavedeviceid": str(device.zwavedeviceid),
            "command": json.dumps({"operation": operation})
        }
        
        try:
            response = await self._async_request(
                "post",
                f"{BASE_URL}/device/operate",
                params=params
            )
            
            return response.get("resultCode") == 0
            
        except Exception as err:
            _LOGGER.error("Operation error for device %s: %s", device.name, str(err))
            return False

    async def _async_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make an async request to the API."""
        try:
            response = await self.hass.async_add_executor_job(
                lambda: getattr(self.session, method)(url, **kwargs)
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Request error: %s", str(err))
            raise

    def _parse_devices(self, data: Dict[str, Any]) -> None:
        """Parse devices from API response."""
        self.devices.clear()
        
        for device in data.get('appliancestatus', []):
            device_name = "Unknown"
            for remote in data.get('remote', []):
                for appliance in remote.get('appliancelist', []):
                    if appliance.get('nuid') == device.get('nuid'):
                        device_name = appliance.get('name', "Unknown")
                        break

            self.devices.append(Device(
                name=device_name,
                device_id=device.get('deviceid', ''),
                device_type=device.get('devicetype', ''),
                status=device.get('status', 0),
                nuid=device.get('nuid', 0),
                battery=device.get('battery', 0),
                last_active_time=device.get('lastactivetime', ''),
                zwavedeviceid=device.get('zwavedeviceid', 0),
                statuses=device.get('statuses')
            ))

    def _organize_rooms(self) -> None:
        """Organize devices by room."""
        self.rooms.clear()
        self.rooms["Unassigned"] = []
        
        for room in self.raw_data.get('rooms', []):
            room_name = room.get('name', 'Unknown')
            self.rooms[room_name] = []
            
            for appliance in room.get('appliancelist', []):
                for device in self.devices:
                    if device.nuid == appliance.get('nuid'):
                        self.rooms[room_name].append(device)

    def _find_unassigned_devices(self) -> None:
        """Find devices not assigned to any room."""
        assigned_nuids = set()
        for room_name, devices in self.rooms.items():
            if room_name != "Unassigned":
                assigned_nuids.update(device.nuid for device in devices)
        
        for device in self.devices:
            if device.nuid not in assigned_nuids:
                self.rooms["Unassigned"].append(device)

    def get_devices_by_type(self, device_type: str) -> List[Device]:
        """Get all devices of a specific type."""
        return [device for device in self.devices if device.device_type == device_type]

    def get_devices_in_room(self, room_name: str) -> List[Device]:
        """Get all devices in a specific room."""
        return self.rooms.get(room_name, [])
