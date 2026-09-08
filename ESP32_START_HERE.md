# ESP32-C3 SuperMini: VS Code에서 업로드하고 센서 CSV 받기

현재 연결된 **보드 1개, BMI270 1개, 압력 4개, SHTC3 4개** 기준입니다.
양발의 보드 2개를 동시에 수집하는 기능은 이번 구성에 포함되지 않습니다.

## 1. 전원을 끄고 PCA9548A 주소부터 수정

**SHTC3 주소는 0x70입니다. PCA9548A 기본 주소 0x70과 겹치므로 반드시 분리하세요.**

- PCA9548A A0 → 3.3V, A1·A2 → GND: 주소 **0x71**
- A0가 이미 GND에 직접 연결되어 있다면 그 연결을 먼저 제거합니다. 전원과 GND를 연결하지 마세요.
- RESET은 노션대로 10kΩ으로 3.3V에 풀업합니다.
- 모듈이 주소 점퍼 방식이면 모듈 설명에 따라 A0 점퍼를 설정합니다.
- 이 펌웨어는 PCA9548A 0x71을 사용합니다. 온습도 센서 주소는 변경하지 않습니다.

| ESP 핀 | 연결 |
|---|---|
| GPIO6 / GPIO7 | I²C SDA / SCL 공통선 → BMI270, PCA9548A 입력 |
| GPIO1 / 3 / 4 / 5 | CD74HC4067 S0 / S1 / S2 / S3 |
| GPIO0 | CD74HC4067 SIG (ADC) |
| 3V3 / GND | 센서·MUX 전원 / 공통 접지 |

CD74HC4067 EN → GND. 압력 4개는 **C0, C2, C4, C6**.
노션의 공통저항 방식: `3V3 → FSR → MUX 채널 → 선택 스위치 → SIG/GPIO0 → 10kΩ → GND`.
각 센서마다 별도 저항을 쓴 분압 회로라면 SIG에 추가 병렬저항을 달지 마세요.
SHTC3 4개는 PCA9548A **SD3/SC3, SD4/SC4, SD5/SC5, SD6/SC6**.
BMI270 모듈은 3.3V/GND/SDA/SCL을 연결하고 INT는 이번 코드에서 쓰지 않습니다.
BMI270 주소는 0x68, 0x69를 순서대로 확인합니다.
레이저 GPIO10은 LOW로 유지하고 진동모터는 구동하지 않습니다.

## 2. 최신 프로젝트 열기

GitHub의 Code → Download ZIP → 새 폴더에 압축 해제.
VS Code → 파일 → 폴더 열기에서 **platformio.ini가 보이는 프로젝트 최상위 폴더**를 엽니다.
기존 데이터가 있는 폴더에 덮어쓰지 말고 새 폴더를 사용하세요.

## 3. ESP에 업로드 (VS Code + PlatformIO)

1. VS Code 확장 탭에서 공식 **PlatformIO IDE** (`platformio.platformio-ide`)를 설치합니다.
2. 프로젝트가 열리면 초기 도구 설치가 끝날 때까지 기다립니다.
3. ESP를 **데이터 전송 가능한 USB 케이블**로 PC에 연결합니다.
4. PlatformIO → Project Tasks → esp32c3 → General → **Build**, 성공하면 **Upload**.
5. 업로드 후 **Monitor**로 `# BMI270 address=0x68` 또는 `0x69`,
   `# PCA9548A address=0x71`과 JSON 출력을 확인합니다.
6. Python 수신 전에 **Monitor를 종료**합니다. 같은 COM 포트는 한 프로그램만 엽니다.

업로드되는 코드: **firmware/capstone_sensor/capstone_sensor.ino**.
**platformio.ini**가 ESP32-C3용 설정과 SparkFun BMI270 라이브러리를 자동 설치합니다.
파일을 ESP 드라이브에 복사하는 방식이 아니라 Upload로 컴파일한 펌웨어를 기록합니다.
보드 이름은 공통 ESP32-C3 빌드 대상으로 `esp32-c3-devkitm-1`을 사용하며,
SuperMini의 USB CDC 설정은 platformio.ini에 포함되어 있습니다.

포트가 여러 개라면 PlatformIO 터미널에서:
```powershell
pio device list
pio run -e esp32c3 -t upload --upload-port COM5
pio device monitor -p COM5 -b 115200
```
COM5는 예시입니다. 실제 포트로 바꾸세요. 모니터 종료는 Ctrl+C.
연결에 실패하면 BOOT를 누른 채 RESET을 눌렀다 놓고 BOOT를 놓은 뒤 다시 업로드하세요.
업로드 후 RESET을 한 번 눌러야 실행되는 보드도 있습니다.

## 4. PC 수신 환경 준비 (카메라 없이)

Python 3.11을 설치한 Windows 기준, VS Code의 새 PowerShell 터미널에서:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-sensors.txt
.\.venv\Scripts\python.exe scripts/capture_sensors.py --list-ports
```
가상환경 활성화 없이 python.exe를 직접 실행하므로 PowerShell 실행 정책 변경이 필요 없습니다.

## 5. 먼저 30초간 센서만 수집

```powershell
.\.venv\Scripts\python.exe scripts/capture_sensors.py --port COM5 --session sensor_test_01 --duration 30
```
압력센서를 하나씩 누르고 IMU를 움직여 값 변화를 확인하세요.
온습도는 초당 한 번 갱신됩니다. 저장 위치:
`data/raw/sensor_test_01/sensor_raw.csv`.
이 폴더 이름은 다음 실험에서 sensor_test_02 등으로 바꾸세요. 기존 세션에 이어쓰지 않습니다.
`--duration 0`은 Ctrl+C까지 계속 수집합니다.

| CSV 열 | 의미 / 순서 |
|---|---|
| timestamp_ms | PC monotonic 수신 시간, 카메라와 같은 시계 |
| pressure_0~3 | C0, C2, C4, C6의 12비트 ADC 원시값(대략 0~4095), 보정된 압력 단위 아님 |
| acc_x/y/z | m/s², 중력 포함 |
| gyro_x/y/z | °/s |
| temperature_c_0~3 | CH3, CH4, CH5, CH6의 °C |
| humidity_pct_0~3 | 같은 채널 순서의 상대습도 %RH |
| environment_age_ms | 마지막 온습도 읽기 완료 후 지난 시간 |
| device_ms / seq | ESP 측 시간 / 패킷 순번, 누락·지연 점검용 |

온습도 값은 다음 1초 갱신까지 반복됩니다. 새 독립 측정 50개가 아닙니다.
센서 읽기 실패는 JSON null → CSV NaN으로 기록합니다. 센서가 없다고 0을 만들어 넣지 않습니다.
FSR 숫자가 나온다는 것만으로 센서 연결이 검증되는 것은 아닙니다. 실제로 누르는 채널이 변해야 합니다.
CSV는 VS Code나 Excel에서 열 수 있습니다. 측정 데이터는 GitHub에 올라가지 않습니다.

## 6. 카메라와 함께 기록 (센서 단독 확인 후)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/download_model.py
.\.venv\Scripts\python.exe scripts/capture_calibration.py --config config.hardware.json --sensor serial --port COM5 --session normal_real_01 --duration 30
```
같은 세션 폴더에 pose_raw.csv와 온습도가 포함된 sensor_raw.csv가 따로 저장됩니다.
원래 config.json의 8채널 mock 설정은 유지하며, 실제 배선에는 config.hardware.json을 사용합니다.
센서는 별도 수신 스레드가 읽으므로 카메라 처리 후에 밀린 패킷 시간을 찍는 문제를 줄입니다.
수신 시간은 실제 센서 측정 시각과 완전히 같지는 않습니다. 엄밀한 동기화 검증은 별도입니다.

걸음 데이터 생성 전 **config.hardware.json의 step_detection.heel_channels를 실제 뒤꿈치 센서 인덱스로 수정**하세요.
현재 [0,1]은 기존 프로젝트 값이며 아직 발바닥 위치가 확인되지 않았습니다.
그 후 카메라도 함께 수집한 정상 보행 세션에만:
```powershell
.\.venv\Scripts\python.exe scripts/build_dataset.py --config config.hardware.json --session normal_real_01 --label Normal
```
온습도 원시 열은 synced_timeseries.csv에 유지되고, 걸음별 평균이 dataset_steps.csv에 추가됩니다.
센서 단독 테스트에는 pose_raw.csv가 없으므로 이 명령을 실행하지 않습니다.

## 문제 확인

- `PCA9548A address=0x00`: A0/A1/A2, 입력 SDA/SCL, RESET, 전원 확인. 0x70에서 사용하지 마세요.
- 온습도만 NaN: CH3~6의 SD/SC, 각 센서 전원, PCA 주소 확인. 잘못된 체크섬도 NaN 처리합니다.
- BMI270 address=0x00 또는 IMU NaN: 전원·SDA/SCL 확인 후 RESET. 초기화 시 없던 BMI를 연결했으면 RESET 필요.
- 압력이 고정: EN=GND, SIG=GPIO0, 공통접지, 10kΩ 분압과 실제 C0/C2/C4/C6 연결 확인.
- 포트 사용 중/Access denied: PlatformIO Monitor, Arduino Serial Monitor, 다른 Python 수신기를 종료.
- 10초 동안 수신 없음: 실제 COM 포트, 업로드 성공 여부, USB 케이블, RESET 확인.
- `invalid` 증가: 이전 펌웨어나 채널 수가 다른 설정인지 확인. config.hardware.json은 압력 4개입니다.
- 온습도는 정상이어도 발의 어느 위치인지 아직 모릅니다. 채널 이름을 위치로 임의 지정하지 않았습니다.

## 참고 자료

- [Sensirion SHTC3 데이터시트](https://sensirion.com/file/datasheet_shtc3)
- [TI PCA9548A 주소 설정](https://www.ti.com/lit/ds/symlink/pca9548a.pdf)
- [SparkFun BMI270 라이브러리](https://github.com/sparkfun/SparkFun_BMI270_Arduino_Library)
- [PlatformIO ESP32-C3 보드 설정](https://docs.platformio.org/en/latest/boards/espressif32/esp32-c3-devkitm-1.html)
