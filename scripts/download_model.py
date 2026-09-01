\
from pathlib import Path
from urllib.request import urlretrieve
URL=("https://storage.googleapis.com/mediapipe-models/" "pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task")
DEST=Path("models/pose_landmarker_lite.task")
DEST.parent.mkdir(parents=True,exist_ok=True)
if DEST.exists(): print(f"Already exists: {DEST}")
else:
    print("Downloading MediaPipe Pose Landmarker model..."); urlretrieve(URL,DEST); print(f"Saved: {DEST}")
