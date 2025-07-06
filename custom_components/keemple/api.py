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
    
    def channel_status(self):
        """Get status for specific channel or first status for single devices."""
        if self.channel is not None:
            if self.statuses and len(self.statuses) >= self.channel:
                status = self.statuses[self.channel - 1]
                _LOGGER.debug(
                    "Device %s channel %s status: %s (from statuses: %s)",
                    self.name,
                    self.channel,
                    status,
                    self.statuses
                )
                return status
            _LOGGER.warning(
                "Device %s channel %s has invalid status array: %s",
                self.name,
                self.channel,
                self.statuses
            )
            return 0
        return self.statuses[0] if self.statuses else 0

    def set_channel_status(self, val):
        """Set status for specific channel or first status for single devices."""
        if self.channel is not None:
            if not self.statuses:
                self.statuses = [0] * max(DUAL_CHANNELS)
            while len(self.statuses) < self.channel:
                self.statuses.append(0)
            self.statuses[self.channel - 1] = val
            _LOGGER.debug(
                "Set device %s channel %s to %s (statuses: %s)",
                self.name,
                self.channel,
                val,
                self.statuses
            )
        else:
            if not self.statuses:
                self.statuses = [0]
            self.statuses[0] = val

    @property
    def internal_id(self) -> str:
        """Return internal ID for device tracking."""
        if self.channel is not None:
            return f"{self.nuid}_{self.channel}"
        return str(self.nuid)

    def update_from_status(self, new_status: dict) -> None:
        """Update device state from new status data."""
        self.status = new_status.get('status', self.status)
        new_statuses = new_status.get('statuses')
        
        _LOGGER.debug(
            "Updating device %s (channel: %s) with new statuses: %s",
            self.name,
            self.channel,
            new_statuses
        )
        
        if isinstance(new_statuses, str):
            try:
                self.statuses = [float(x) for x in new_statuses.strip('[]').split(',')]
            except (ValueError, AttributeError):
                _LOGGER.warning("Failed to parse statuses string: %s", new_statuses)
                return
        elif isinstance(new_statuses, list):
            self.statuses = new_statuses
        
        _LOGGER.debug(
            "Device %s (channel: %s) updated statuses: %s",
            self.name,
            self.channel,
            self.statuses
        )

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
        _LOGGER.debug("Starting data update cycle")

        if not self._authenticated:
            _LOGGER.debug("Not authenticated, performing login")
            await self.async_login()

        params = {
            "platform": DEFAULT_PLATFORM,
        }
        
        try:
            _LOGGER.debug("Making API request to querychangeddata2")
            data = await self._async_request(
                "post",
                f"{BASE_URL}/data/querychangeddata2",
                params=params
            )
            
            if data:
                _LOGGER.debug("Received data from API: %s", data)
                old_states = {d.nuid: (d.status, d.statuses) for d in self.devices}
                self._parse_devices(data)
                
                # Log state changes
                for device in self.devices:
                    if device.nuid in old_states:
                        old_status, old_statuses = old_states[device.nuid]
                        if old_status != device.status or old_statuses != device.statuses:
                            _LOGGER.debug("Device %s state changed: %s -> %s, %s -> %s",
                                        device.name,
                                        old_status, device.status,
                                        old_statuses, device.statuses)
                
                self._organize_rooms()
                self._find_unassigned_devices()
                return data

            _LOGGER.debug("No data received from API")
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
                # device.status = 1 if operation == "open" else 0
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
        existing_devices = {device.internal_id: device for device in self.devices}
        new_devices = []

        for device_status in data.get('appliancestatus', []):
            nuid = device_status.get('nuid')
            
            # Find device name
            device_name = "Unknown"
            for remote in data.get('remote', []):
                for appliance in remote.get('appliancelist', []):
                    if appliance.get('nuid') == nuid:
                        device_name = appliance.get('name', "Unknown")
                        break

            device_type = device_status.get('devicetype', '')

            if device_type == DEVICE_TYPE_LIGHT_DUAL:
                _LOGGER.debug("Processing dual light device: %s", device_name)
                for channel in DUAL_CHANNELS:
                    device_key = f"{nuid}_{channel}"
                    if device_key in existing_devices:
                        # Update existing device
                        _LOGGER.debug("Updating existing dual light channel %d: %s", 
                                    channel, device_status)
                        existing_devices[device_key].update_from_status(device_status)
                        new_devices.append(existing_devices[device_key])
                    else:
                        # Create new device
                        _LOGGER.debug("Creating new dual light channel %d", channel)
                        new_device = Device(
                            name=device_name,
                            device_id=device_status.get('deviceid', ''),
                            device_type=device_type,
                            status=device_status.get('status', 0),
                            nuid=nuid,
                            battery=device_status.get('battery', 0),
                            last_active_time=device_status.get('lastactivetime', ''),
                            zwavedeviceid=device_status.get('zwavedeviceid', 0),
                            statuses=device_status.get('statuses', []),
                            channel=channel
                        )
                        new_devices.append(new_device)
            else:
                device_key = str(nuid)
                if device_key in existing_devices:
                    existing_devices[device_key].update_from_status(device_status)
                    new_devices.append(existing_devices[device_key])
                else:
                    new_devices.append(Device(
                        name=device_name,
                        device_id=device_status.get('deviceid', ''),
                        device_type=device_type,
                        status=device_status.get('status', 0),
                        nuid=nuid,
                        battery=device_status.get('battery', 0),
                        last_active_time=device_status.get('lastactivetime', ''),
                        zwavedeviceid=device_status.get('zwavedeviceid', 0),
                        statuses=device_status.get('statuses', [])
                    ))

        self.devices = new_devices
        _LOGGER.debug("Updated devices: %s", 
                     [(d.name, d.channel, d.status, d.statuses) for d in self.devices])
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
