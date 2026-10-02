import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class RoiService:
    @staticmethod
    def get_roi_bounds(roi_coords, frame_width, frame_height):
        """
        Converts ROI points (normalized 0.0-1.0 or absolute pixels) to pixel bounding coordinates.
        roi_coords: list of dicts [{'x': float, 'y': float}, ...] or list of tuples
        Returns clamped: (min_x, min_y, max_x, max_y) in frame pixels.
        """
        if not roi_coords or len(roi_coords) < 2:
            return 0, 0, 0, 0

        xs = []
        ys = []
        for pt in roi_coords:
            if isinstance(pt, dict):
                x_val = pt.get("x", pt.get("X", 0.0))
                y_val = pt.get("y", pt.get("Y", 0.0))
            elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                x_val, y_val = pt[0], pt[1]
            else:
                continue
            xs.append(float(x_val))
            ys.append(float(y_val))

        if not xs or not ys:
            return 0, 0, 0, 0

        # Detect whether stored coordinates are normalized (<= 1.0) or absolute pixels (> 1.0)
        is_normalized = max(xs) <= 1.0 and max(ys) <= 1.0

        if is_normalized:
            x1 = min(xs) * frame_width
            x2 = max(xs) * frame_width
            y1 = min(ys) * frame_height
            y2 = max(ys) * frame_height
        else:
            x1 = min(xs)
            x2 = max(xs)
            y1 = min(ys)
            y2 = max(ys)

        min_x = max(0, min(frame_width - 1, int(min(x1, x2))))
        max_x = max(0, min(frame_width, int(max(x1, x2))))
        min_y = max(0, min(frame_height - 1, int(min(y1, y2))))
        max_y = max(0, min(frame_height, int(max(y1, y2))))

        return min_x, min_y, max_x, max_y

    @staticmethod
    def detect_motion_in_roi(
        current_frame,
        prev_gray_roi,
        min_x,
        min_y,
        max_x,
        max_y,
        motion_threshold: float = 0.02,
        min_motion_area: int = 300,
    ):
        """
        OpenCV Motion Detection inside ROI:
        1. Extract ROI slice
        2. Convert to grayscale & GaussianBlur
        3. Compare with prev_gray_roi using cv2.absdiff
        4. Apply threshold & dilate (morphology)
        5. Find contours and filter by min_motion_area
        6. Calculate motion ratio = changed_pixels / total_roi_pixels
        Returns: (motion_detected, motion_ratio, current_gray_roi)
        """
        if max_x <= min_x or max_y <= min_y:
            return False, 0.0, None

        roi_frame = current_frame[min_y:max_y, min_x:max_x]
        if roi_frame.size == 0:
            logger.warning("[ROI ERROR] ROI contains no pixels")
            return False, 0.0, None

        gray_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        blurred_roi = cv2.GaussianBlur(gray_roi, (21, 21), 0)

        if prev_gray_roi is None or prev_gray_roi.shape != blurred_roi.shape:
            return False, 0.0, blurred_roi

        frame_diff = cv2.absdiff(prev_gray_roi, blurred_roi)
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        total_roi_pixels = float((max_x - min_x) * (max_y - min_y))
        motion_pixel_count = 0
        significant_motion = False

        for c in contours:
            area = cv2.contourArea(c)
            if area >= min_motion_area:
                motion_pixel_count += int(area)
                significant_motion = True

        motion_ratio = (
            motion_pixel_count / total_roi_pixels if total_roi_pixels > 0 else 0.0
        )
        motion_detected = significant_motion and (motion_ratio >= motion_threshold)

        return motion_detected, round(motion_ratio, 4), blurred_roi

    @staticmethod
    def check_intrusion(bbox, frame_width, frame_height, roi_coords):
        """
        Calculates whether a detected person bounding box [x1, y1, x2, y2] is inside the ROI.
        Returns: (inside, (cx, cy), (foot_inside, center_inside, box_overlap))
        """
        if not roi_coords or len(roi_coords) < 2:
            return False, (0, 0), (False, False, False)

        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0

        min_x, min_y, max_x, max_y = RoiService.get_roi_bounds(
            roi_coords, frame_width, frame_height
        )

        # Foot point (ground contact point of person)
        foot_inside = (min_x <= center_x <= max_x) and (min_y <= y2 <= max_y)
        
        # Center point
        center_inside = (min_x <= center_x <= max_x) and (min_y <= center_y <= max_y)

        # Box overlap (intersection)
        box_overlap = (x1 < max_x and x2 > min_x and y1 < max_y and y2 > min_y)

        inside = foot_inside or center_inside or box_overlap

        return inside, (int(center_x), int(center_y)), (bool(foot_inside), bool(center_inside), bool(box_overlap))


