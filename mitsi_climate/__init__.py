import homeassistant.components.mysensors.climate as myclimate
from .climate import async_setup_platform

"""Example Mitsi integration."""
DOMAIN = "mitsi_climate"

myclimate.async_setup_platform = async_setup_platform

async def async_setup(hass, config):
    # Return boolean to indicate that initialization was successful.
    return True