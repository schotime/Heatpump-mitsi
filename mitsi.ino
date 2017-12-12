#define MY_RADIO_NRF24
#define MY_REPEATER_FEATURE

#include <MySensors.h>
#include <HeatPump.h>
#include <MemoryFree.h>
 
#define CHILD_ID_HVAC 1
#define SEND_DELAY 250
#define RAND_MIN 300000
#define RAND_MAX 600000

MyMessage msgHVACStatus(CHILD_ID_HVAC, V_STATUS);
MyMessage msgHVACFlowState(CHILD_ID_HVAC, V_VAR1);
MyMessage msgHVACFlowStateInit(CHILD_ID_HVAC, V_HVAC_FLOW_STATE);
MyMessage msgHVACSpeed(CHILD_ID_HVAC, V_VAR2);
MyMessage msgHVACTemp(CHILD_ID_HVAC, V_TEMP);
MyMessage msgHVACSetPointC(CHILD_ID_HVAC, V_HVAC_SETPOINT_COOL);
MyMessage msgHVACVane(CHILD_ID_HVAC, V_VAR3);
MyMessage msgMemory(CHILD_ID_HVAC, V_VAR4);

HeatPump hp;
heatpumpSettings newSettings;
long lastSend = 0;
boolean sendUpdate = false;

void setup() {
  wait(500);

  hp.connect(&Serial);
  hp.setSettingsChangedCallback(hpSettingsChanged);
  hp.setRoomTempChangedCallback(hpRoomTempChanged);

  randomSeed(analogRead(0));
}

void presentation() {
  sendSketchInfo("Mitsi", "3.43");
  present(CHILD_ID_HVAC, S_HVAC, "Unit");
}

void hpSettingsChanged() {
  hpSendSettings(true);
}

void hpSendSettings(bool updateTime) {
  send(msgHVACStatus.set(hp.getPowerSettingBool()));   wait(SEND_DELAY);
  send(msgHVACSpeed.set(hp.getFanSpeed()));            wait(SEND_DELAY);
  send(msgHVACFlowState.set(hp.getModeSetting()));     wait(SEND_DELAY);
  send(msgHVACSetPointC.set(hp.getTemperature(), 1));  wait(SEND_DELAY);
  send(msgHVACVane.set(hp.getVaneSetting()));          wait(SEND_DELAY);
  if (hp.getRoomTemperature() > 0) {
    send(msgHVACTemp.set(hp.getRoomTemperature(), 1)); wait(SEND_DELAY);
  }
  send(msgMemory.set(freeMemory()));                   wait(SEND_DELAY);
  send(msgHVACFlowStateInit.set(hp.getPowerSettingBool() ? "HeatOn" : "Off"));

  if (updateTime) {
    lastSend = millis();
  }
}

void hpRoomTempChanged(float newRoomTemp) {
  send(msgHVACTemp.set(newRoomTemp, 1));
}
 
void loop() {
  if (sendUpdate) {
    hp.setSettings(newSettings);
    hp.update();
    sendUpdate = false;
  }
  else {
    hp.sync();
    if (sendUpdate == false) {
      newSettings = hp.getSettings();
    }
    if (millis() > (lastSend + (random(RAND_MIN, RAND_MAX)))) {
      hpSettingsChanged();
    }
  }
}

void receive(const MyMessage &message) {
  switch (message.type) {
    case V_STATUS:
      newSettings.power = message.getBool() ? HeatPump::POWER_MAP[1] : HeatPump::POWER_MAP[0];
      break;
      
    case V_HVAC_SETPOINT_COOL:
      newSettings.temperature = message.getFloat();
      break;

    case V_VAR1:
      if (strcmp(message.getString(), HeatPump::POWER_MAP[0]) == 0) {
        newSettings.power = HeatPump::POWER_MAP[0];
      } 
      else {
        newSettings.power = HeatPump::POWER_MAP[1];
        newSettings.mode = HeatPump::MODE_MAP[HeatPump::lookupByteMapIndex(HeatPump::MODE_MAP, 5, message.getString())];
      }
      break;

    case V_VAR2:
      newSettings.fan = HeatPump::FAN_MAP[HeatPump::lookupByteMapIndex(HeatPump::FAN_MAP, 6, message.getString())];
      break;
        
    case V_VAR3:
      newSettings.vane = HeatPump::VANE_MAP[HeatPump::lookupByteMapIndex(HeatPump::VANE_MAP, 7, message.getString())];
      break;

    case V_VAR4:
      hpSendSettings(false);
      break;
  }

  if (newSettings != hp.getSettings()) {
    sendUpdate = true;
  }
}
