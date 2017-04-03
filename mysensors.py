"""
mysensors platform that offers a Climate(MySensors-HVAC) component.
For more details about this platform, please refer to the documentation
https://home-assistant.io/components/climate.mysensors
"""
import logging

from homeassistant.components import mysensors
from homeassistant.components.climate import (
    STATE_COOL, STATE_HEAT, STATE_OFF, STATE_AUTO, ClimateDevice,
    ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW)
from homeassistant.const import TEMP_CELSIUS, TEMP_FAHRENHEIT, ATTR_TEMPERATURE

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the mysensors climate."""
    
    if discovery_info is None:
        return
 
    gateways = hass.data.get(mysensors.MYSENSORS_GATEWAYS)
    if not gateways:
        return

    for gateway in gateways:
        if float(gateway.protocol_version) < 1.5:
            continue
        pres = gateway.const.Presentation
        set_req = gateway.const.SetReq
        map_sv_types = {
            pres.S_HVAC: [set_req.V_VAR1],
        }
        devices = {}
        gateway.platform_callbacks.append(mysensors.pf_callback_factory(
            map_sv_types, devices, MyMitsi, add_devices))


class MyMitsi(mysensors.MySensorsDeviceEntity, ClimateDevice):
    """Representation of a MyMitsi hvac."""

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
        return float(self._values.get(self.gateway.const.SetReq.V_TEMP))

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
        return float(temp)

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        set_req = self.gateway.const.SetReq
        if set_req.V_HVAC_SETPOINT_HEAT in self._values:
            return self._values.get(set_req.V_HVAC_SETPOINT_COOL)

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        set_req = self.gateway.const.SetReq
        if set_req.V_HVAC_SETPOINT_COOL in self._values:
            return self._values.get(set_req.V_HVAC_SETPOINT_HEAT)

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        if self._values.get(self.gateway.const.SetReq.V_STATUS) == "1":
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

        print(self.gateway.optimistic)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[set_req.V_STATUS] = "1" if operation_mode != "OFF" else "0"
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
        set_req = self.gateway.const.SetReq
        node = self.gateway.sensors[self.node_id]
        child = node.children[self.child_id]
        for value_type, value in child.values.items():
            _LOGGER.debug('%s: value_type %s, value = %s', self._name, value_type, value)
            self._values[value_type] = value

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