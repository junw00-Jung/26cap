\
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from capstone_gait.step_features import detect_heel_strikes, make_step_segments


def test_detect_regular_heel_strikes():
    t = np.arange(0, 4000, 10)
    phase = (t % 1000)
    heel = np.where((phase >= 50) & (phase < 250), 700.0, 0.0)
    df = pd.DataFrame({
        "timestamp_ms": t,
        "pressure_0": heel,
        "pressure_1": heel * 0.9,
    })
    strikes = detect_heel_strikes(df, (0,1), refractory_ms=450)
    assert len(strikes) >= 3
    segs = make_step_segments(df, strikes, min_step_ms=700, max_step_ms=1300)
    assert len(segs) >= 2
