"""
mysensors platform that offers a Climate(MySensors-HVAC) component.
For more details about this platform, please refer to the documentation
https://home-assistant.io/components/climate.mysensors
"""
import logging

from homeassistant.components import mysensors
from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW, DOMAIN, STATE_AUTO,
    STATE_COOL, STATE_HEAT, STATE_OFF, STATE_DRY, STATE_FAN_ONLY, ClimateDevice,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_FAN_MODE, SUPPORT_OPERATION_MODE,
    SUPPORT_SWING_MODE)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

_LOGGER = logging.getLogger(__name__)

DICT_HA_TO_MYS = {
    STATE_OFF: 'OFF',
    STATE_HEAT: 'HEAT',
    STATE_COOL: 'COOL',
    STATE_AUTO: 'AUTO',
    STATE_DRY: 'DRY',
    STATE_FAN_ONLY: 'FAN'
}
DICT_MYS_TO_HA = {
    'OFF': STATE_OFF,
    'HEAT': STATE_HEAT,
    'COOL': STATE_COOL,
    'AUTO': STATE_AUTO,
    'DRY': STATE_DRY,
    'FAN': STATE_FAN_ONLY
}

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE |
                 SUPPORT_OPERATION_MODE | SUPPORT_SWING_MODE)

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Setup the mysensors climate."""
    mysensors.setup_mysensors_platform(
        hass, DOMAIN, discovery_info, MyMitsi, async_add_devices=async_add_devices)

class MyMitsi(mysensors.device.MySensorsEntity, ClimateDevice):
    """Representation of a MyMitsi hvac."""

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def assumed_state(self):
        """Return True if unable to access real state of entity."""
        return self.gateway.optimistic

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return (TEMP_CELSIUS
                if self.gateway.metric else TEMP_FAHRENHEIT)

    @property
    def current_temperature(self):
        """Return the current temperature."""
        value = self._values.get(self.gateway.const.SetReq.V_TEMP)
        if value is not None:
            value = float(value)
        return value

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        set_req = self.gateway.const.SetReq
        if set_req.V_HVAC_SETPOINT_COOL in self._values and \
                set_req.V_HVAC_SETPOINT_HEAT in self._values:
            return None
        temp = self._values.get(set_req.V_HVAC_SETPOINT_COOL)
        if temp is None:
            temp = self._values.get(set_req.V_HVAC_SETPOINT_HEAT)
        if temp is not None:
            temp = float(temp)
        return temp

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        set_req = self.gateway.const.SetReq
        if set_req.V_HVAC_SETPOINT_HEAT in self._values:
            temp = self._values.get(set_req.V_HVAC_SETPOINT_COOL)
            return float(temp) if temp is not None else None

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        set_req = self.gateway.const.SetReq
        if set_req.V_HVAC_SETPOINT_COOL in self._values:
            temp = self._values.get(set_req.V_HVAC_SETPOINT_HEAT)
            return float(temp) if temp is not None else None

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        if self._values.get(self.gateway.const.SetReq.V_STATUS) == "on":
            return DICT_MYS_TO_HA[self._values.get(self.gateway.const.SetReq.V_VAR1)]
        return "off"

    @property
    def operation_list(self):
        """List of available operation modes."""
        return [STATE_OFF, STATE_COOL, STATE_HEAT, STATE_DRY, STATE_FAN_ONLY, STATE_AUTO]

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return self._values.get(self.gateway.const.SetReq.V_VAR2)

    @property
    def fan_list(self):
        """List of available fan modes."""
        return ["AUTO", "QUIET", "1", "2", "3", "4"]

    @property
    def current_swing_mode(self):
        """Return the swing setting."""
        return self._values.get(self.gateway.const.SetReq.V_VAR3)

    @property
    def swing_list(self):
        """List of available swing modes."""
        return ["AUTO", "SWING", "1", "2", "3", "4", "5"]

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""

        set_req = self.gateway.const.SetReq
        temp = kwargs.get(ATTR_TEMPERATURE)
        low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        heat = self._values.get(set_req.V_HVAC_SETPOINT_HEAT)
        cool = self._values.get(set_req.V_HVAC_SETPOINT_COOL)
        updates = ()
        if temp is not None:
            if heat is not None:
                # Set HEAT Target temperature
                value_type = set_req.V_HVAC_SETPOINT_HEAT
            elif cool is not None:
                # Set COOL Target temperature
                value_type = set_req.V_HVAC_SETPOINT_COOL
            if heat is not None or cool is not None:
                updates = [(value_type, temp)]
        elif all(val is not None for val in (low, high, heat, cool)):
            updates = [
                (set_req.V_HVAC_SETPOINT_HEAT, low),
                (set_req.V_HVAC_SETPOINT_COOL, high)]
        for value_type, value in updates:
            self.gateway.set_child_value(
                self.node_id, self.child_id, value_type, value)
            if self.gateway.optimistic:
                # optimistically assume that switch has changed state
                self._values[value_type] = value
                self.async_schedule_update_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set new target temperature."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(self.node_id, self.child_id,
                                     set_req.V_VAR2, fan_mode)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[set_req.V_VAR2] = fan_mode
            self.async_schedule_update_ha_state()

    async def async_set_operation_mode(self, operation_mode):
        """Set new operation mode."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(self.node_id, self.child_id,
                                     set_req.V_VAR1,
                                     DICT_HA_TO_MYS[operation_mode])

        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[set_req.V_STATUS] = "on" if operation_mode != "off" else "off"
            self._values[set_req.V_VAR1] = DICT_HA_TO_MYS[operation_mode]
            self.async_schedule_update_ha_state()

    async def async_set_swing_mode(self, swing_mode):
        """Set new swing mode."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(self.node_id, self.child_id,
                                     set_req.V_VAR3, swing_mode)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[set_req.V_VAR3] = swing_mode
            self.async_schedule_update_ha_state()

    async def async_update(self):
        """Update the controller with the latest value from a sensor."""
        await super().async_update()
        mapped_value = DICT_MYS_TO_HA.get(self._values[self.value_type].upper())
        if mapped_value:
            self._values[self.value_type] = mapped_value

    def set_humidity(self, humidity):
        """Set new target humidity."""
        _LOGGER.error("Service Not Implemented yet")

    def turn_away_mode_on(self):
        """Turn away mode on."""
        _LOGGER.error("Service Not Implemented yet")

    def turn_away_mode_off(self):
        """Turn away mode off."""
        _LOGGER.error("Service Not Implemented yet")

    def turn_aux_heat_on(self):
        """Turn auxillary heater on."""
        self._aux = True
        self.schedule_update_ha_state()

    def turn_aux_heat_off(self):
        """Turn auxillary heater off."""
        self._aux = False
        self.schedule_update_ha_state()
