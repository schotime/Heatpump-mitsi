#define MY_RADIO_NRF24
#define MY_REPEATER_FEATURE

#include <MySensors.h>
#include <HeatPump.h>
 
#define CHILD_ID_HVAC 1
#define UNIT_ON "ON"
#define UNIT_OFF "OFF"

MyMessage msgHVACStatus(CHILD_ID_HVAC, V_STATUS);
MyMessage msgHVACFlowState(CHILD_ID_HVAC, V_VAR1);
MyMessage msgHVACSpeed(CHILD_ID_HVAC, V_VAR2);
MyMessage msgHVACTemp(CHILD_ID_HVAC, V_TEMP);
MyMessage msgHVACSetPointC(CHILD_ID_HVAC, V_HVAC_SETPOINT_COOL);
MyMessage msgHVACVane(CHILD_ID_HVAC, V_VAR3);
//MyMessage msgPong(CHILD_ID_HVAC, V_VAR4);
 
HeatPump hp;
heatpumpSettings newSettings;
long lastSend = 0;
boolean sendUpdate = false;

void setup() {
  sleep(500);
  
  hp.connect(&Serial);
 //while(!hp.connect(&Serial)) { }
  
  hp.setSettingsChangedCallback(hpSettingsChanged);
  hp.setRoomTempChangedCallback(hpRoomTempChanged);
}

void presentation() {
  sendSketchInfo("Mitsi", "2.0");
  present(CHILD_ID_HVAC, S_HVAC, "Unit");
}

void hpSettingsChanged() {
  send(msgHVACStatus.set(hp.getPowerSettingBool()));
  send(msgHVACSpeed.set(hp.getFanSpeed().c_str()));
  send(msgHVACFlowState.set(hp.getModeSetting().c_str()));
  send(msgHVACSetPointC.set(hp.getTemperature()));
  send(msgHVACVane.set(hp.getVaneSetting().c_str()));
  if (hp.getRoomTemperature() > 0) {
    send(msgHVACTemp.set(hp.getRoomTemperature(), 1));
  }
  lastSend = millis();
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
    if (millis() > (lastSend + 30000L)) {
      hpSettingsChanged();
    }
  }
  
  sleep(1000);
}

void receive(const MyMessage &message) {
  String recvData = message.data;
  recvData.trim();

  newSettings = hp.getSettings();
  
  switch (message.type) {
    case V_STATUS:
      newSettings.power = message.getBool() ? UNIT_ON : UNIT_OFF;
      break;
      
    case V_HVAC_SETPOINT_COOL:
      newSettings.temperature = recvData.toFloat();
      break;

    case V_VAR1:
      if (recvData.equalsIgnoreCase(UNIT_OFF)) {
        newSettings.power = UNIT_OFF;
      } 
      else {
        newSettings.power = UNIT_ON;
        newSettings.mode = recvData;
      }
      break;

    case V_VAR2:
      newSettings.fan = recvData;
      break;
        
    case V_VAR3:
      newSettings.vane = recvData;
      break;
  }

  if (newSettings != hp.getSettings()) {
    sendUpdate = true;
  }
}
