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
DEFAULT_SCAN_INTERVAL: Final = 30

# Device Types
DEVICE_TYPE_LIGHT: Final = "41"
DEVICE_TYPE_LIGHT_DUAL: Final = "42"

DUAL_CHANNELS: Final = [1, 2]  # Channels for dual devices

# Error messages
ERROR_AUTH: Final = "invalid_auth"
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_UNKNOWN: Final = "unknown"
