# Capstone Gait MVP

> **코드 구조와 각 파일의 역할이 헷갈리면 먼저 [`PROJECT_GUIDE.md`](./PROJECT_GUIDE.md)를 보세요.**  
> `scripts/`, `src/`, `tests/`, `data/` 폴더가 각각 왜 존재하는지와 전체 데이터 흐름을 한국어로 정리해두었습니다.

현재까지 설계한 내용을 실제 코드 구조로 만든 MVP입니다.

## 구현 범위

### 1) MediaPipe 신체 좌표 정규화
- Hip center를 원점으로 사용
- 기본 scale: hip width
- `config.json`에서 `hip_width / shoulder_width / torso_length / robust` 선택 가능
- `ankle height / hip width` 비율도 별도 feature로 저장
- Knee flexion, ankle joint angle, trunk lean, pelvic tilt, shoulder tilt 계산

### 2) Dynamic + Reference landmark 기반 재활 평가
- Dynamic target: knee flexion ROM
- Reference/postural features: trunk lean, pelvic tilt, shoulder tilt
- ROM PASS/FAIL과 posture PASS/FAIL을 따로 판정
- 예: knee 50° 달성했어도 몸통 기울기 한계를 넘으면 INCORRECT

### 3) Camera + insole pressure + IMU timestamp 동기화
- 카메라와 센서 원시 데이터를 별도 CSV로 저장
- 둘 다 PC의 monotonic clock(ms)을 사용
- 후처리에서 sensor timeline에 pose feature를 interpolation
- pose sample gap이 너무 크면 NaN 처리

### 4) 한 걸음 단위 ML dataset 생성
- heel pressure rising edge -> heel strike
- heel strike ~ next heel strike -> step
- 한 step의 ROM, pressure peak/mean, IMU RMS/std/peak 등을 feature로 변환
- calibration data는 `Normal` label

---

## 설치 권장 환경
- Windows 10/11
- Python 3.11
- webcam
- 처음에는 실제 ESP32 없이 mock sensor로 실행 가능

## 0. 프로젝트 폴더에서 가상환경
PowerShell:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 1. MediaPipe 모델 다운로드
```powershell
python scripts/download_model.py
```

## 2. 하드웨어 없이 30초 정상 보행 calibration
```powershell
python scripts/capture_calibration.py --session normal_01 --sensor mock --duration 30
```

웹캠 창에서 `q`를 누르면 중간 종료됩니다.

생성:
```text
data/raw/normal_01/pose_raw.csv
data/raw/normal_01/sensor_raw.csv
```

## 3. timestamp 동기화 + 한 걸음 feature dataset
```powershell
python scripts/build_dataset.py --session normal_01 --label Normal
```

생성:
```text
data/processed/normal_01/synced_timeseries.csv
data/processed/normal_01/dataset_steps.csv
```

`dataset_steps.csv`의 **한 행 = 한 걸음** 입니다.

## 4. 재활 ROM + 보상동작 평가
왼쪽 무릎, 목표 flexion 50°:
```powershell
python scripts/rehab_live.py --side left --target 50
```

처음 3초간 편하게 서 있으면 trunk/pelvis/shoulder 기준 자세를 잡습니다.
이후 무릎을 굽혔다 다시 펴면 한 repetition으로 판정합니다.

출력:
- ROM PASS/FAIL
- POSTURE PASS/FAIL
- FINAL CORRECT/INCORRECT

---

# 실제 ESP32 연결

현재 collector는 아래 JSON 한 줄을 ESP32에서 받을 수 있도록 만들어 두었습니다.

```json
{"pressure":[100,120,40,30,250,220,80,50],"accel":[0.1,-0.2,9.7],"gyro":[1.2,20.3,-2.0]}
```

각 패킷 뒤에 newline(`\n`)이 있어야 합니다.

실행:
```powershell
python scripts/capture_calibration.py --session normal_real_01 --sensor serial --port COM5 --duration 30
```

중요: ESP32의 `millis()`와 PC 카메라 시간을 바로 비교하지 않습니다.
PC가 센서 패킷을 받은 순간 `time.perf_counter_ns()` 기반 timestamp를 부여하여
카메라와 같은 clock domain으로 맞춥니다.

---

# 정규화 수식

Landmark `p=(x,y)`, hip center `h`, body scale `s`:

```text
p_normalized = (p - h) / s
```

기본:
```text
s = hip_width
```

추가 feature:
```text
ankle_height_over_hip_width
= abs(ankle_y - hip_center_y) / hip_width
```

카메라가 멀어지면 numerator와 denominator가 함께 작아지므로
raw coordinate보다 distance change에 덜 민감한 feature를 만드는 목적입니다.

주의:
몸이 카메라에 대해 크게 회전하면 영상상의 hip width 자체가 줄어듭니다.
그 경우 `config.json`의 scale_mode를 `torso_length` 또는 `robust`로 바꾸고,
반드시 여러 거리/회전 조건에서 repeatability를 검증해야 합니다.

---

# 연구 데이터 관점에서 중요한 점

`Normal` calibration만으로 Normal/FoG classifier를 완성할 수는 없습니다.
현재 코드는 **개인 정상 보행 baseline dataset을 만드는 단계**입니다.

추후 FoG classifier를 만들 때는:
1. FoG가 포함된 데이터 수집/확보
2. FoG onset/offset label 정의
3. subject-independent train/validation split
4. step/window feature 비교
가 별도로 필요합니다.

---

# 테스트
```powershell
pytest -q
```

# Codex
Codex가 저장소를 수정할 때 프로젝트 규칙을 놓치지 않도록 루트에 `AGENTS.md`가 있습니다.
Codex에게 첫 요청으로:

```text
Read AGENTS.md and README.md, run tests, and only then make changes.
```

를 주는 것을 권장합니다.

GitHub/Codex 연결 순서는 `GITHUB_CODEX_SETUP.md` 참고.
