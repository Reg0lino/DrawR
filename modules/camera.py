import cv2
import os
import logging

logger = logging.getLogger(__name__)

class Camera:
    def __init__(self, camera_index=None):
        if camera_index is None:
            camera_index = int(os.getenv('CAMERA_INDEX', 0))
        # Use the default backend, just like test_camera.py
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            logger.error(f"Camera at index {camera_index} could not be opened.")

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            logger.error("Failed to read frame from camera.")
        return ret, frame