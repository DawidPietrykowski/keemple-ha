# Keemple Home

Keemple Home is a custom Home Assistant integration that allows connecting to Keemple devices.

Currently supported devices:
- **Light switches** :bulb:
- **Blinds** :white_square_button:
- **Thermostats** :thermometer:

## Recommended: [HACS](https://hacs.xyz/) installation

[![Open your Home Assistant instance and open the Keemple Home integration inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DawidPietrykowski&repository=keemple-ha&category=integration)

_or_

1. Install HACS if you don't have it already
2. Open HACS in Home Assistant
3. Add custom repository with type "Integration" and url: https://github.com/DawidPietrykowski/keemple-ha.git
4. Click the download button.

## Manual installation

- Copy custom_components/keemple folder into <config directory>/custom_components
- Restart Home Assistant

# Configuration

[![Open your Home Assistant instance and start setting up a new Keemple Home integration instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=keemple)

- Open "Integrations" tab
- Select "Add integration"
- Pick "Keemple Home" from the list
- Enter credentials (`country_code` can be kept `0`)
