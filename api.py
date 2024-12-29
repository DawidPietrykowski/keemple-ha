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
    DEFAULT_PLATFORM,
    DEVICE_TYPE_LIGHT_DUAL,
    DUAL_CHANNELS,
    BLIND_MIN_POSITION,
    BLIND_MAX_POSITION,
    DEVICE_TYPE_BLIND,
    TEMP_TARGET_IDX,
    TEMP_CURRENT_IDX,
    POWER_STATE_IDX
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
    statuses: Optional[list] = None
    channel: Optional[int] = None  # Add channel support
    def __post_init__(self):
        """Convert statuses string to list if needed."""
        if isinstance(self.statuses, str):
            try:
                self.statuses = [float(x) for x in self.statuses.strip('[]').split(',')]
            except (ValueError, AttributeError):
                self.statuses = []
    @property
    def unique_id(self) -> str:
        """Return unique ID for Home Assistant."""
        base_id = f"{DOMAIN}_{self.device_type}_{self.nuid}"
        if self.channel is not None:
            return f"{base_id}_channel_{self.channel}"
        return base_id
    @property
    def display_name(self) -> str:
        """Return display name including channel if applicable."""
        if self.channel is not None:
            return f"{self.name} Channel {self.channel}"
        return self.name
    
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

        url = f"{BASE_URL}/device/operate"
        
        params = {
            "platform": DEFAULT_PLATFORM,
            "zwavedeviceid": str(device.zwavedeviceid),
            "command": json.dumps({"operation": operation})
        }
        
        # Add channel parameter for dual devices
        if device.channel is not None:
            params["channel"] = str(device.channel)
        
        try:
            response = await self._async_request("post", url, params=params)
            if response.get("resultCode") == 0:
                device.status = 1 if operation == "open" else 0
                return True
            
            _LOGGER.error(
                "Failed to operate device %s: %s", 
                device.display_name, 
                response.get("resultMessage", "Unknown error")
            )
            return False
            
        except Exception as err:
            _LOGGER.error("Error operating device %s: %s", device.display_name, str(err))
            return False

    async def operate_blind(self, device: Device, operation: str, value: Optional[int] = None) -> bool:
        """Operate a blind (open/close/stop with optional position)."""
        if not self._authenticated:
            await self.async_login()

        url = f"{BASE_URL}/device/operate"
        
        command = {"operation": operation}
        if value is not None:
            command["value"] = value

        params = {
            "platform": DEFAULT_PLATFORM,
            "zwavedeviceid": str(device.zwavedeviceid),
            "command": json.dumps(command)
        }
        
        try:
            response = await self._async_request("post", url, params=params)
            if response.get("resultCode") == 0:
                if value is not None:
                    device.status = value
                elif operation == "close":
                    device.status = BLIND_MIN_POSITION
                elif operation == "open":
                    device.status = BLIND_MAX_POSITION
                return True
            
            _LOGGER.error(
                "Failed to operate blind %s: %s", 
                device.name, 
                response.get("resultMessage", "Unknown error")
            )
            return False
            
        except Exception as err:
            _LOGGER.error("Error operating blind %s: %s", device.name, str(err))
            return False

    async def set_heater_temperature(self, device: Device, temperature: float) -> bool:
        """Set heater target temperature."""
        if not self._authenticated:
            await self.async_login()

        url = f"{BASE_URL}/device/operate"
        
        command = {
            "mode": 1,
            "temperature": temperature
        }

        params = {
            "platform": DEFAULT_PLATFORM,
            "zwavedeviceid": str(device.zwavedeviceid),
            "command": json.dumps(command)
        }
        
        try:
            response = await self._async_request("post", url, params=params)
            if response.get("resultCode") == 0:
                if isinstance(device.statuses, list) and len(device.statuses) > TEMP_TARGET_IDX:
                    device.statuses[TEMP_TARGET_IDX] = float(temperature)
                return True
            
            _LOGGER.error(
                "Failed to set temperature for heater %s: %s", 
                device.name, 
                response.get("resultMessage", "Unknown error")
            )
            return False
            
        except Exception as err:
            _LOGGER.error("Error setting temperature for heater %s: %s", device.name, str(err))
            return False

    async def set_heater_power(self, device: Device, power: int) -> bool:
        """Set heater power state."""
        if not self._authenticated:
            await self.async_login()

        url = f"{BASE_URL}/device/operate"
        
        command = {
            "power": power
        }

        params = {
            "platform": DEFAULT_PLATFORM,
            "zwavedeviceid": str(device.zwavedeviceid),
            "command": json.dumps(command)
        }
        
        try:
            response = await self._async_request("post", url, params=params)
            if response.get("resultCode") == 0:
                if isinstance(device.statuses, list) and len(device.statuses) > POWER_STATE_IDX:
                    device.statuses[POWER_STATE_IDX] = 1.0 if power else 0.0
                return True
            
            _LOGGER.error(
                "Failed to set power for heater %s: %s", 
                device.name, 
                response.get("resultMessage", "Unknown error")
            )
            return False
            
        except Exception as err:
            _LOGGER.error("Error setting power for heater %s: %s", device.name, str(err))
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

            device_type = device.get('devicetype', '')

            status = device.get('status', 0)
            if device_type == DEVICE_TYPE_BLIND:
                status = max(BLIND_MIN_POSITION, min(BLIND_MAX_POSITION, status))   
            
            statuses = device.get('statuses')
            if isinstance(statuses, str):
                try:
                    statuses = [float(x) for x in statuses.strip('[]').split(',')]
                except (ValueError, AttributeError):
                    statuses = []

            # For dual devices (type 42), create two devices
            if device_type == DEVICE_TYPE_LIGHT_DUAL:
                for channel in DUAL_CHANNELS:
                    self.devices.append(Device(
                        name=device_name,
                        device_id=device.get('deviceid', ''),
                        device_type=device_type,
                        status=status,
                        nuid=device.get('nuid', 0),
                        battery=device.get('battery', 0),
                        last_active_time=device.get('lastactivetime', ''),
                        zwavedeviceid=device.get('zwavedeviceid', 0),
                        statuses=statuses,
                        channel=channel
                    ))
            else:
                # Single devices
                self.devices.append(Device(
                    name=device_name,
                    device_id=device.get('deviceid', ''),
                    device_type=device_type,
                    status=status,
                    nuid=device.get('nuid', 0),
                    battery=device.get('battery', 0),
                    last_active_time=device.get('lastactivetime', ''),
                    zwavedeviceid=device.get('zwavedeviceid', 0),
                    statuses=statuses
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
