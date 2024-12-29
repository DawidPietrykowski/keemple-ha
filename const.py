"""Constants for the Keemple integration."""
from typing import Final

DOMAIN: Final = "keemple"
NAME: Final = "Keemple"

# Configuration
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_COUNTRY_CODE: Final = "country_code"

# API
BASE_URL: Final = "https://webconsole.keemple.com/iremote"
DEFAULT_PLATFORM: Final = "8"

# Defaults
DEFAULT_COUNTRY_CODE: Final = "0"
DEFAULT_SCAN_INTERVAL: Final = 5
DEFAULT_REFRESH_DELAY: Final = 0

# Device Types
DEVICE_TYPE_LIGHT: Final = "41"
DEVICE_TYPE_LIGHT_DUAL: Final = "42"
DEVICE_TYPE_BLIND: Final = "13"
DEVICE_TYPE_HEATER: Final = "51"

DUAL_CHANNELS: Final = [1, 2]  # Channels for dual devices

# Blind Constants
BLIND_MIN_POSITION: Final = 0
BLIND_MAX_POSITION: Final = 99
HA_MAX_POSITION: Final = 100    # Home Assistant's max position

# Heater Constants
HEATER_MIN_TEMP: Final = 5
HEATER_MAX_TEMP: Final = 30
HEATER_STEP: Final = 0.5

# Heater State Indices
TEMP_TARGET_IDX: Final = 0    # Target temperature (22.0)
TEMP_UNKNOWN1_IDX: Final = 1  # Unknown value (71.6)
TEMP_CURRENT_IDX: Final = 2   # Current temperature (21)
TEMP_UNKNOWN2_IDX: Final = 3  # Unknown value (69)
POWER_STATE_IDX: Final = 4    # Power state (1 = on, 0 = off)

# Error messages
ERROR_AUTH: Final = "invalid_auth"
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_UNKNOWN: Final = "unknown"
