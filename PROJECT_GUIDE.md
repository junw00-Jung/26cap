# 26cap 프로젝트 파일 역할 설명

이 문서는 `26cap` 저장소 안의 각 파일과 폴더가 **무슨 역할을 하는지** 빠르게 이해하기 위한 안내서입니다.

---

# 1. 전체 흐름부터 보기

이 프로젝트는 크게 두 가지 기능을 구현합니다.

## A. 초기 보행 Calibration / 학습데이터 생성

```text
웹캠
  ↓
MediaPipe Pose
  ↓
Hip center 기준 좌표 정규화
  ↓
Knee / Ankle / Trunk / Pelvis feature 계산

압력 깔창 ─┐
           ├─ 같은 PC timestamp 사용
IMU ───────┘
  ↓
시간축 동기화
  ↓
Heel Strike 검출
  ↓
한 걸음 단위 분할
  ↓
한 걸음의 특징값 추출
  ↓
dataset_steps.csv
  ↓
Normal label을 가진 개인 정상 보행 데이터
```

## B. 재활 동작 평가

```text
웹캠
 ↓
MediaPipe
 ↓
Dynamic Point 평가
  └─ Knee ROM이 목표값까지 도달했는가?

Reference / Postural Point 평가
  ├─ 몸통을 과도하게 기울였는가?
  ├─ 골반이 과도하게 기울었는가?
  └─ 어깨가 과도하게 기울었는가?

 ↓
ROM PASS / FAIL
POSTURE PASS / FAIL
 ↓
최종 Correct / Incorrect Movement
```

---

# 2. 저장소 전체 구조

```text
26cap/
│
├── README.md
├── PROJECT_GUIDE.md
├── AGENTS.md
├── GITHUB_CODEX_SETUP.md
├── config.json
├── requirements.txt
├── .gitignore
│
├── scripts/
│   ├── download_model.py
│   ├── capture_calibration.py
│   ├── build_dataset.py
│   └── rehab_live.py
│
├── src/
│   └── capstone_gait/
│       ├── __init__.py
│       ├── geometry.py
│       ├── pose_engine.py
│       ├── sensors.py
│       ├── synchronization.py
│       ├── step_features.py
│       ├── rehab_logic.py
│       └── visualization.py
│
├── tests/
│   ├── test_geometry.py
│   ├── test_rehab.py
│   └── test_steps.py
│
├── models/
│   └── pose_landmarker_lite.task   # 실행 후 다운로드됨
│
├── data/
│   ├── raw/
│   └── processed/
│
└── .github/
    └── workflows/
        └── tests.yml
```

---

# 3. 가장 먼저 봐야 하는 파일

## `README.md`

프로젝트의 **사용 설명서**입니다.

주요 내용:
- 프로그램 설치 방법
- 가상환경 생성
- MediaPipe 모델 다운로드
- Calibration 실행
- dataset 생성
- 재활 모드 실행
- ESP32 연결 형식

처음 프로젝트를 실행할 때는 이 파일부터 보면 됩니다.

---

## `PROJECT_GUIDE.md`

현재 읽고 있는 문서입니다.

코드를 직접 수정하기 전에

> “이 파일이 왜 있는 거지?”

를 확인하는 용도입니다.

---

## `config.json`

프로그램에서 사용하는 **설정값을 한 곳에 모아놓은 파일**입니다.

예를 들어:

```json
"camera_index": 0
```

은 사용할 카메라 번호입니다.

```json
"scale_mode": "hip_width"
```

는 MediaPipe 좌표 정규화 기준을 `Hip Width`로 사용한다는 뜻입니다.

또한 다음과 같은 값들이 들어갑니다.

- 압력센서 개수
- IMU sampling rate
- ESP32 COM port
- Heel Strike 검출 조건
- 목표 Knee ROM
- 몸통 기울기 허용범위
- 골반 기울기 허용범위

즉, **연구 실험에서 바뀔 수 있는 수치는 최대한 이 파일에서 수정**하도록 만든 구조입니다.

---

# 4. `scripts/` 폴더

여기는 사용자가 **직접 실행하는 프로그램**들이 들어 있습니다.

쉽게 말하면 `src/`가 엔진이라면 `scripts/`는 실행 버튼입니다.

---

## `scripts/download_model.py`

### 역할

MediaPipe Pose 모델 파일을 다운로드합니다.

처음 한 번 실행:

```powershell
python scripts/download_model.py
```

그러면

```text
models/pose_landmarker_lite.task
```

파일이 생성됩니다.

이 모델이 없으면 MediaPipe 자세 측정을 실행할 수 없습니다.

---

## `scripts/capture_calibration.py`

### 역할

**초기 정상 보행 Calibration 데이터를 수집하는 메인 프로그램**입니다.

이 프로젝트에서 가장 중요한 실행 파일 중 하나입니다.

실행 예:

```powershell
python scripts/capture_calibration.py --session normal_01 --sensor mock --duration 30
```

이 프로그램이 동시에 하는 일:

```text
웹캠 촬영
 ↓
MediaPipe landmark 검출
 ↓
정규화된 관절 feature 계산
 ↓
pose_raw.csv 저장

동시에

Pressure + IMU 수집
 ↓
sensor_raw.csv 저장
```

여기서는 아직 데이터를 한 걸음 단위로 합치지 않습니다.

**Raw 데이터는 Raw 데이터 그대로 보존**합니다.

출력:

```text
data/raw/normal_01/pose_raw.csv
data/raw/normal_01/sensor_raw.csv
```

---

## `scripts/build_dataset.py`

### 역할

Calibration에서 모은 Raw 데이터를 **AI 학습에 사용하기 좋은 한 걸음 단위 데이터로 변환**합니다.

입력:

```text
pose_raw.csv
sensor_raw.csv
```

처리 과정:

```text
Timestamp 동기화
 ↓
Heel Strike 검출
 ↓
한 걸음 단위 분할
 ↓
각 걸음의 특징값 계산
 ↓
Normal label 부여
```

출력:

```text
data/processed/normal_01/synced_timeseries.csv
data/processed/normal_01/dataset_steps.csv
```

가장 중요한 것은

```text
dataset_steps.csv
```

입니다.

여기서는

> 한 행 = 한 걸음

이 됩니다.

예:

```text
Step 1
- Knee ROM
- Ankle ROM
- Pressure Peak
- Pressure Mean
- Acceleration RMS
- Gyroscope RMS
- Step Time
- Label = Normal
```

---

## `scripts/rehab_live.py`

### 역할

**재활 운동을 실시간으로 평가**합니다.

예:

```powershell
python scripts/rehab_live.py --side left --target 50
```

목표:

```text
Left Knee Flexion = 50°
```

을 주면 두 가지를 따로 확인합니다.

### 1. Dynamic Motion

```text
Knee가 실제로 50°까지 움직였는가?
```

### 2. Compensation / Posture

```text
50°를 만들기 위해
몸통을 옆으로 심하게 기울이지 않았는가?
골반을 틀지 않았는가?
어깨를 기울이지 않았는가?
```

따라서 결과는 예를 들어

```text
ROM      : PASS
POSTURE  : FAIL
FINAL    : INCORRECT
```

처럼 나옵니다.

---

# 5. `src/capstone_gait/` 폴더

여기는 프로젝트의 **실제 계산 로직**이 들어 있습니다.

`scripts/`에서 이 코드들을 불러와 사용합니다.

---

## `geometry.py`

### 역할

각도, 거리, 좌표 정규화 같은 **기초 수학 계산**을 담당합니다.

주요 기능:

- 두 점 사이 거리
- 두 점의 중간점
- 세 점을 이용한 관절각 계산
- Trunk lean 계산
- Pelvic tilt 계산
- Shoulder tilt 계산
- Hip center 기준 좌표 정규화
- RMS 계산

예를 들어 무릎각은

```text
Hip - Knee - Ankle
```

세 점으로 계산합니다.

MediaPipe 계산의 가장 기초가 되는 파일입니다.

---

## `pose_engine.py`

### 역할

**MediaPipe를 실제로 돌리는 핵심 파일**입니다.

웹캠 영상 한 프레임이 들어오면:

```text
영상
 ↓
MediaPipe Pose Landmark
 ↓
Left/Right Hip
Left/Right Knee
Left/Right Ankle
Shoulder
Heel
Foot Index
 ↓
각도 계산
 ↓
좌표 정규화
 ↓
Feature 출력
```

을 수행합니다.

이 파일에서 우리가 이야기했던 정규화가 실제로 구현됩니다.

기본 구조:

```text
Hip Center = (Left Hip + Right Hip) / 2
```

그리고

```text
Normalized Point
= (Point - Hip Center) / Hip Width
```

형태로 변환합니다.

또한

```text
Ankle Height / Hip Width
```

feature도 여기서 계산합니다.

즉 **카메라와 사람 사이 거리 변화의 영향을 줄이는 부분**입니다.

---

## `sensors.py`

### 역할

깔창 압력센서와 IMU 데이터를 담당합니다.

두 가지 모드가 있습니다.

### MockSensorSource

실제 센서가 없을 때 가짜 데이터를 생성합니다.

따라서 지금 당장 ESP32가 없어도 전체 프로그램을 테스트할 수 있습니다.

### SerialSensorSource

실제 ESP32에서 데이터를 받아옵니다.

ESP32가 다음과 같은 데이터를 보낸다고 가정합니다.

```json
{
  "pressure": [100,120,40,30,250,220,80,50],
  "accel": [0.1,-0.2,9.7],
  "gyro": [1.2,20.3,-2.0]
}
```

그리고 PC가 데이터를 받은 순간 timestamp를 부여합니다.

---

## `synchronization.py`

### 역할

**MediaPipe와 Pressure/IMU의 시간축을 맞추는 파일**입니다.

왜 필요한가?

예를 들어:

```text
Camera     = 약 30 Hz
Pressure   = 약 100 Hz
IMU        = 약 100 Hz
```

라면 측정 시점이 서로 다릅니다.

그래서

```text
Pose timestamp
Sensor timestamp
```

를 기준으로 같은 시간축으로 맞춥니다.

현재 구조에서는 센서 timeline에 맞춰 Pose 값을 interpolation합니다.

---

## `step_features.py`

### 역할

연속적인 센서 데이터를 **한 걸음 단위 데이터로 바꾸는 파일**입니다.

핵심 과정:

```text
Heel Pressure 상승
 ↓
Heel Strike
 ↓
다음 Heel Strike
 ↓
1 Step
```

그리고 한 Step에서 다음과 같은 특징을 뽑습니다.

### MediaPipe
- Knee ROM
- Ankle ROM
- Trunk lean 변화
- Pelvic tilt 변화

### Pressure
- Peak pressure
- Mean pressure
- Total pressure

### IMU
- Mean
- Standard deviation
- RMS
- Absolute peak

따라서 엄청 많은 Raw 데이터를

```text
수십 개의 Feature
```

로 압축합니다.

---

## `rehab_logic.py`

### 역할

재활운동에서

> 운동을 했는가?

와

> 올바르게 했는가?

를 판단하는 로직입니다.

### Dynamic Point 평가

현재는 Knee Flexion을 사용합니다.

```text
Peak Knee Flexion >= Target ROM
```

이면 ROM PASS입니다.

### Reference / Postural Point 평가

초기 자세와 비교해

- Trunk lean
- Pelvic tilt
- Shoulder tilt

가 허용 범위를 넘어가는지 확인합니다.

따라서

```text
Knee ROM = 55°
Target   = 50°
```

이어도

```text
Trunk Lean 변화 = 16°
허용값 = 10°
```

이면

```text
ROM PASS
POSTURE FAIL
FINAL INCORRECT
```

가 됩니다.

---

## `visualization.py`

### 역할

OpenCV 웹캠 화면에

```text
Knee angle
ROM
Trunk lean
PASS / FAIL
```

같은 글자를 표시하는 보조 파일입니다.

실제 분석 알고리즘보다는 **화면 표시 담당**입니다.

---

## `__init__.py`

Python에게

```text
capstone_gait 폴더를 하나의 Python package로 사용한다
```

고 알려주는 파일입니다.

직접 수정할 일은 거의 없습니다.

---

# 6. `tests/` 폴더

코드를 수정했을 때 기존 기능이 망가지지 않았는지 자동으로 확인합니다.

실행:

```powershell
pytest -q
```

---

## `test_geometry.py`

확인하는 것:

- 일직선 무릎각이 약 180°인지
- 좌표 크기가 달라져도 정규화 결과가 유지되는지
- 몸통이 수직이면 trunk lean이 0°인지

즉 `geometry.py`의 계산이 맞는지 확인합니다.

---

## `test_rehab.py`

재활 판정 로직을 확인합니다.

예:

```text
Knee 55°
Trunk 정상
→ Correct
```

```text
Knee 55°
Trunk 16° 기울어짐
→ Incorrect
```

같은 상황을 자동으로 테스트합니다.

---

## `test_steps.py`

압력 데이터에서

```text
Heel Strike
```

를 정상적으로 찾고

```text
한 걸음
```

단위로 분리할 수 있는지 확인합니다.

---

# 7. `data/` 폴더

실험 데이터를 저장합니다.

## `data/raw/`

원본 데이터입니다.

예:

```text
pose_raw.csv
sensor_raw.csv
```

**원본 데이터이므로 가능하면 수정하거나 덮어쓰지 않는 것이 좋습니다.**

---

## `data/processed/`

가공된 데이터를 저장합니다.

예:

```text
synced_timeseries.csv
dataset_steps.csv
```

AI 학습에는 주로 이쪽 데이터가 사용됩니다.

---

# 8. `models/` 폴더

MediaPipe 모델 파일을 저장합니다.

```text
pose_landmarker_lite.task
```

등이 들어갑니다.

GitHub에는 모델 자체를 올리지 않고 필요할 때 `download_model.py`로 다운로드하도록 되어 있습니다.

---

# 9. `AGENTS.md`

이 파일은 사람이 실행하는 코드가 아닙니다.

**Codex에게 주는 프로젝트 규칙**입니다.

Codex가 코드를 수정할 때 다음 원칙을 지키도록 합니다.

예:

- Raw pixel 좌표를 그대로 비교하지 말 것
- Hip center 기반 정규화를 유지할 것
- Raw data를 보존할 것
- 한 프레임이 아니라 한 걸음 단위 dataset을 만들 것
- Normal 데이터에 임의로 FoG label을 붙이지 말 것
- ROM 평가와 보상동작 평가를 분리할 것

즉 Codex가 프로젝트 방향을 마음대로 바꾸지 않게 하는 역할입니다.

---

# 10. `GITHUB_CODEX_SETUP.md`

Codex와 GitHub 저장소를 연결해서 개발할 때 사용하는 안내서입니다.

Codex에게 어떤 프롬프트를 주는 것이 좋은지도 들어 있습니다.

---

# 11. `.github/workflows/tests.yml`

GitHub Actions 설정입니다.

GitHub에 코드를 push하거나 Pull Request를 만들면 자동으로

```text
pytest
```

를 실행하도록 만든 파일입니다.

즉 코드가 망가진 상태로 올라가는 것을 막기 위한 자동 검사입니다.

---

# 12. `.gitignore`

GitHub에 올릴 필요가 없는 파일을 지정합니다.

예:

```text
.venv/
__pycache__/
models/*.task
data/raw/*
data/processed/*
```

가상환경, 실제 실험 데이터, 큰 모델파일 등을 실수로 GitHub에 올리지 않도록 합니다.

---

# 13. `requirements.txt`

프로젝트에 필요한 Python 라이브러리 목록입니다.

```powershell
pip install -r requirements.txt
```

를 실행하면 필요한 패키지를 한 번에 설치합니다.

예:

- MediaPipe
- OpenCV
- NumPy
- Pandas
- PySerial
- Pytest

---

# 14. 지금 단계에서 실제로 자주 만질 파일

현재 캡스톤 진행 단계에서는 모든 파일을 알 필요는 없습니다.

우선 아래 파일만 기억하면 됩니다.

| 파일 | 언제 사용하는가 |
|---|---|
| `config.json` | 센서 개수, 목표 ROM, threshold 등을 바꿀 때 |
| `capture_calibration.py` | 정상 보행 데이터를 촬영/수집할 때 |
| `build_dataset.py` | Raw 데이터를 한 걸음 dataset으로 만들 때 |
| `rehab_live.py` | 재활 운동을 실시간 평가할 때 |
| `pose_engine.py` | MediaPipe 정규화/관절각 계산을 수정할 때 |
| `sensors.py` | 실제 ESP32/압력센서/IMU 연결을 수정할 때 |
| `step_features.py` | 한 걸음 feature를 추가하거나 바꿀 때 |
| `rehab_logic.py` | 보상동작 판단 기준을 수정할 때 |

나머지는 당장 깊게 이해하지 않아도 됩니다.

---

# 15. 추천 개발 순서

현재 프로젝트는 아래 순서로 개발하면 가장 이해하기 쉽습니다.

```text
1. Mock sensor + Webcam으로 프로그램 실행

2. MediaPipe 각도와 정규화 값이 제대로 나오는지 확인

3. 실제 압력센서 + IMU를 ESP32에 연결

4. sensors.py의 Serial 입력으로 실제 데이터 수집

5. timestamp 동기화 확인

6. Heel Strike와 Step segmentation 확인

7. 실제 사람의 정상 보행 dataset 생성

8. 재활 ROM + compensation logic 검증

9. 이후 FoG 데이터 확보

10. Normal / FoG AI 모델 학습
```

현재는 **1~8번까지의 기반을 만드는 단계**라고 보면 됩니다.
