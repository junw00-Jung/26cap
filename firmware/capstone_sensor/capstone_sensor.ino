#include <Arduino.h>
#include <Wire.h>
#include <SparkFun_BMI270_Arduino_Library.h>
#include <math.h>

// ESP32-C3 SuperMini, one board: 4 FSR + 4 SHTC3 + one BMI270.
const uint8_t SELECT_PINS[] = {1, 3, 4, 5};
const uint8_t PRESSURE_CHANNELS[] = {0, 2, 4, 6};
const uint8_t ENV_CHANNELS[] = {3, 4, 5, 6};
const uint8_t ADC_PIN = 0, SDA_PIN = 6, SCL_PIN = 7;
const uint32_t SAMPLE_MS = 20, ENV_MS = 1000;
BMI270 imu;
uint8_t muxAddress = 0, imuAddress = 0;
float temperatures[4] = {NAN,NAN,NAN,NAN};
float humidities[4] = {NAN,NAN,NAN,NAN};
bool envStarted[4] = {};
bool envPending = false;
uint32_t envStart = 0, envUpdated = 0, lastSample = 0, sequence = 0;
bool hasEnv = false;

bool ack(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}
bool muxWrite(uint8_t mask) {
  if (!muxAddress) return false;
  Wire.beginTransmission(muxAddress); Wire.write(mask);
  return Wire.endTransmission() == 0;
}
bool shtCommand(uint16_t command) {
  Wire.beginTransmission(0x70);
  Wire.write(uint8_t(command >> 8)); Wire.write(uint8_t(command));
  return Wire.endTransmission() == 0;
}
uint8_t crc8(const uint8_t *bytes) {
  uint8_t crc = 0xFF;
  for (int i=0;i<2;i++) {
    crc ^= bytes[i];
    for (int b=0;b<8;b++) crc = (crc & 0x80) ? (crc << 1) ^ 0x31 : crc << 1;
  }
  return crc;
}
void number(float value) {
  if (isfinite(value)) Serial.print(value, 3); else Serial.print("null");
}
void floatArray(const float *values, int count) {
  Serial.print('[');
  for (int i=0;i<count;i++) { if(i) Serial.print(','); number(values[i]); }
  Serial.print(']');
}
void environmentTick() {
  if (!muxAddress) return;
  if (!envPending && uint32_t(millis()-envStart) >= ENV_MS) {
    for (int i=0;i<4;i++) {
      envStarted[i] = muxWrite(1 << ENV_CHANNELS[i]) && shtCommand(0x3517);
      delayMicroseconds(250);
      envStarted[i] = envStarted[i] && shtCommand(0x7866);
    }
    muxWrite(0);
    envStart = millis(); envPending = true;
  }
  // All sensors convert concurrently; no 4 x 13 ms blocking delay.
  if (envPending && uint32_t(millis()-envStart) >= 15) {
    for (int i=0;i<4;i++) {
      temperatures[i] = humidities[i] = NAN;
      if (muxWrite(1 << ENV_CHANNELS[i]) && envStarted[i]) {
        uint8_t bytes[6];
        if (Wire.requestFrom(uint8_t(0x70), uint8_t(6)) == 6) {
          for (int j=0;j<6;j++) bytes[j] = Wire.read();
          if (crc8(bytes)==bytes[2] && crc8(bytes+3)==bytes[5]) {
            temperatures[i] = -45.0f + 175.0f * ((bytes[0]<<8)|bytes[1]) / 65536.0f;
            humidities[i] = 100.0f * ((bytes[3]<<8)|bytes[4]) / 65536.0f;
          }
        }
        shtCommand(0xB098);
      }
    }
    muxWrite(0); envUpdated = millis(); hasEnv = true; envPending = false;
  }
}
void setup() {
  // Keep the existing laser control inactive. No haptic commands are issued.
  digitalWrite(10, LOW); pinMode(10, OUTPUT);
  for (uint8_t pin : SELECT_PINS) { digitalWrite(pin, LOW); pinMode(pin, OUTPUT); }
  analogReadResolution(12); analogSetPinAttenuation(ADC_PIN, ADC_11db);
  Serial.begin(115200);
  delay(1500);
  Wire.begin(SDA_PIN, SCL_PIN); Wire.setClock(100000); Wire.setTimeOut(20);
  // IMPORTANT: SHTC3 is 0x70. The PCA/TCA9548A MUST be 0x71 (A0 high).
  if (ack(0x71)) { muxAddress=0x71; muxWrite(0); }
  else Serial.println("# ERROR: PCA9548A must be 0x71: A0=3V3, A1=A2=GND. SHTC3 uses 0x70.");
  for (uint8_t address : {uint8_t(0x68), uint8_t(0x69)}) {
    if (ack(address) && imu.beginI2C(address, Wire)==BMI2_OK) { imuAddress=address; break; }
  }
  Serial.printf("# BMI270 address=0x%02X (0 means unavailable)\n", imuAddress);
  Serial.printf("# PCA9548A address=0x%02X (0 means unavailable)\n", muxAddress);
  Serial.println("# FSR order C0,C2,C4,C6; SHTC3 order CH3,CH4,CH5,CH6; null=missing/error");
  envStart = millis()-ENV_MS;
}
void loop() {
  environmentTick();
  if (uint32_t(millis()-lastSample) < SAMPLE_MS) { delay(1); return; }
  lastSample=millis();
  float pressure[4];
  for(int i=0;i<4;i++) {
    for(int b=0;b<4;b++) digitalWrite(SELECT_PINS[b], (PRESSURE_CHANNELS[i]>>b)&1);
    delayMicroseconds(200); analogRead(ADC_PIN);
    uint32_t sum=0; for(int n=0;n<4;n++) sum+=analogRead(ADC_PIN);
    pressure[i]=sum/4.0f;
  }
  float accel[3]={NAN,NAN,NAN}, gyro[3]={NAN,NAN,NAN};
  if (imuAddress && imu.getSensorData()==BMI2_OK) {
    // SparkFun acceleration is g; the PC pipeline expects m/s^2.
    accel[0]=imu.data.accelX*9.80665f; accel[1]=imu.data.accelY*9.80665f; accel[2]=imu.data.accelZ*9.80665f;
    gyro[0]=imu.data.gyroX; gyro[1]=imu.data.gyroY; gyro[2]=imu.data.gyroZ;
  }
  Serial.print("{\"seq\":"); Serial.print(sequence++);
  Serial.print(",\"device_ms\":"); Serial.print(lastSample);
  Serial.print(",\"pressure\":"); floatArray(pressure,4);
  Serial.print(",\"accel\":"); floatArray(accel,3);
  Serial.print(",\"gyro\":"); floatArray(gyro,3);
  Serial.print(",\"temperature_c\":"); floatArray(temperatures,4);
  Serial.print(",\"humidity_pct\":"); floatArray(humidities,4);
  Serial.print(",\"environment_age_ms\":");
  if(hasEnv) Serial.print(uint32_t(millis()-envUpdated)); else Serial.print("null");
  Serial.println('}');
}
