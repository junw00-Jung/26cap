\
from __future__ import annotations
import cv2


def put_lines(frame, lines, x=15, y=30, dy=26):
    for i, text in enumerate(lines):
        yy = y + i * dy
        cv2.putText(frame, str(text), (x, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, str(text), (x, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 1, cv2.LINE_AA)
    return frame
