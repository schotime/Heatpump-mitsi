import logging
import homeassistant.components.mysensors.climate as myclimate
from .climate import async_setup_entry

_LOGGER = logging.getLogger(__name__)

"""Example Mitsi integration."""
DOMAIN = "mitsi_climate"

myclimate.async_setup_entry = async_setup_entry

async def async_setup(hass, config):
    # Return boolean to indicate that initialization was successful.
    return True