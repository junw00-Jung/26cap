# Codex project instructions

## Goal
Build a research prototype for personalized gait calibration and rehabilitation assessment.

## Non-negotiable design rules
1. Never compare raw image pixel coordinates across camera distances.
2. Pose features must use hip-center as the body origin and a configurable body scale.
3. Keep raw camera-derived pose and raw insole/IMU streams separate; stamp both with the same PC monotonic clock.
4. Synchronize only in an offline/processing step. Preserve the raw files.
5. Build ML samples at step/gait-cycle level, not one training row per video frame.
6. Normal calibration sessions receive `Normal` labels only. Do not invent FoG labels.
7. Rehab evaluation must report two independent results:
   - target dynamic motion / ROM
   - compensatory movement from reference/postural landmarks
8. Add or update tests when changing geometry, synchronization, segmentation, or rehab logic.
9. Keep thresholds configurable in `config.json`; do not hard-code research thresholds.
10. Treat this as a prototype, not a medical diagnostic device.

## Current pipeline
Camera -> MediaPipe Pose -> hip-centered/body-scaled pose features
Insole pressure + IMU -> sensor stream
Both -> monotonic timestamp -> offline synchronization
Synced series -> heel-strike segmentation -> one-row-per-step features -> Normal label

## Future work
- Replace mock sensor stream with ESP32 serial/BLE data.
- Validate pressure channel mapping against the physical insole.
- Collect FoG data with an appropriate labeling protocol.
- Add subject/session IDs and train/validation split by subject.
- Quantify normalization repeatability at multiple camera distances and yaw angles.
