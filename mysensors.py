"""
mysensors platform that offers a Climate(MySensors-HVAC) component.
For more details about this platform, please refer to the documentation
https://home-assistant.io/components/climate.mysensors
"""
import logging

from homeassistant.components import mysensors
from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW, DOMAIN, STATE_AUTO,
    STATE_COOL, STATE_HEAT, STATE_OFF, ClimateDevice,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_TARGET_TEMPERATURE_HIGH,
    SUPPORT_TARGET_TEMPERATURE_LOW, SUPPORT_FAN_MODE, SUPPORT_OPERATION_MODE,
    SUPPORT_SWING_MODE)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_TARGET_TEMPERATURE_HIGH |
                 SUPPORT_TARGET_TEMPERATURE_LOW | SUPPORT_FAN_MODE |
                 SUPPORT_OPERATION_MODE | SUPPORT_SWING_MODE)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the mysensors climate."""
    mysensors.setup_mysensors_platform(
        hass, DOMAIN, discovery_info, MyMitsi, add_devices=add_devices)

class MyMitsi(mysensors.MySensorsEntity, ClimateDevice):
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
            return float(self._values.get(set_req.V_HVAC_SETPOINT_COOL))

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        set_req = self.gateway.const.SetReq
        if set_req.V_HVAC_SETPOINT_COOL in self._values:
            return float(self._values.get(set_req.V_HVAC_SETPOINT_HEAT))

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        if self._values.get(self.gateway.const.SetReq.V_STATUS) == "on":
            return self._values.get(self.gateway.const.SetReq.V_VAR1)
        return "OFF"

    @property
    def operation_list(self):
        """List of available operation modes."""
        return ["OFF", "COOL", "HEAT", "DRY", "FAN", "AUTO",]

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

    def set_temperature(self, **kwargs):
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
                self.schedule_update_ha_state()

    def set_fan_mode(self, fan):
        """Set new target temperature."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(self.node_id, self.child_id,
                                     set_req.V_VAR2, fan)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[set_req.V_VAR2] = fan
            self.schedule_update_ha_state()

    def set_operation_mode(self, operation_mode):
        """Set new operation mode."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(self.node_id, self.child_id,
                                     set_req.V_VAR1,
                                     operation_mode)

        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[set_req.V_STATUS] = "on" if operation_mode != "OFF" else "off"
            self._values[set_req.V_VAR1] = operation_mode            
            self.schedule_update_ha_state()

    def set_swing_mode(self, swing_mode):
        """Set new swing mode."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(self.node_id, self.child_id,
                                     set_req.V_VAR3, swing_mode)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[set_req.V_VAR3] = swing_mode
            self.schedule_update_ha_state()

    def update(self):
        """Update the controller with the latest value from a sensor."""
        super().update()

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
        _LOGGER.error("Service Not Implemented yet")

    def turn_aux_heat_off(self):
        """Turn auxillary heater off."""
        _LOGGER.error("Service Not Implemented yet")