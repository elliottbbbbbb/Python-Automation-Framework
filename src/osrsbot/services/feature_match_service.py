"""
Feature-Based Template Matching Service

Uses ORB (Oriented FAST and Rotated BRIEF) for rotation and scale-invariant matching.
Better than standard template matching for:
- NPCs at different angles
- Items at different zoom levels
- Rotated objects
- Partially occluded objects

Performance: ~10-50ms per match (slower than template matching but more robust)
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import cv2 as cv
import numpy as np

logger = logging.getLogger(__name__)


class FeatureMatchService:
    """
    Feature-based template matching using ORB detector.

    More robust than standard template matching but slower.
    Use for dynamic content that changes size/rotation.
    """

    def __init__(self, n_features: int = 500, match_threshold: float = 0.7):
        """
        Initialize feature matcher.

        Args:
            n_features: Number of features to detect (more = slower but better)
            match_threshold: Minimum ratio of good matches (0.0-1.0)
        """
        # ORB is patent-free (unlike SIFT) and fast
        self.orb = cv.ORB_create(nfeatures=n_features)
        self.match_threshold = match_threshold

        # BFMatcher (Brute Force Matcher) for matching features
        self.bf_matcher = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=True)

        logger.info(f"FeatureMatchService initialized (n_features={n_features})")

    def find_template(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        min_matches: int = 10
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find template in screenshot using feature matching.

        Args:
            screenshot: Captured screenshot (BGR format)
            template: Template image to find (BGR format)
            min_matches: Minimum number of matching features required

        Returns:
            Tuple of (center_x, center_y, confidence) if found, None otherwise
        """
        try:
            # Convert to grayscale (ORB works on grayscale)
            gray_screenshot = cv.cvtColor(screenshot, cv.COLOR_BGR2GRAY)
            gray_template = cv.cvtColor(template, cv.COLOR_BGR2GRAY)

            # Detect keypoints and compute descriptors
            kp1, des1 = self.orb.detectAndCompute(gray_template, None)
            kp2, des2 = self.orb.detectAndCompute(gray_screenshot, None)

            if des1 is None or des2 is None or len(kp1) < min_matches:
                logger.debug("Not enough features detected")
                return None

            # Match descriptors
            matches = self.bf_matcher.match(des1, des2)

            if len(matches) < min_matches:
                logger.debug(f"Only {len(matches)} matches found (need {min_matches})")
                return None

            # Sort by distance (best matches first)
            matches = sorted(matches, key=lambda x: x.distance)

            # Get coordinates of matched keypoints
            src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

            # Find homography (transformation matrix)
            M, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)

            if M is None:
                logger.debug("Could not find valid homography")
                return None

            # Get template dimensions
            h, w = gray_template.shape

            # Transform template corners to screenshot space
            corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
            transformed = cv.perspectiveTransform(corners, M)

            # Calculate center point
            center = np.mean(transformed, axis=0)[0]
            center_x, center_y = int(center[0]), int(center[1])

            # Calculate confidence based on number of inliers
            inliers = np.sum(mask)
            confidence = inliers / len(matches)

            if confidence < self.match_threshold:
                logger.debug(f"Confidence too low: {confidence:.3f} < {self.match_threshold}")
                return None

            logger.debug(
                f"Feature match found at ({center_x}, {center_y}) "
                f"with {inliers}/{len(matches)} inliers (confidence: {confidence:.3f})"
            )

            return (center_x, center_y, confidence)

        except Exception as e:
            logger.error(f"Error in feature matching: {e}")
            return None

    def find_template_multiscale(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        scales: list[float] = [0.8, 1.0, 1.2],
        min_matches: int = 10
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find template at multiple scales (zoom levels).

        Args:
            screenshot: Captured screenshot
            template: Template image to find
            scales: List of scale factors to try
            min_matches: Minimum matching features

        Returns:
            Best match across all scales, or None
        """
        best_match = None
        best_confidence = 0.0

        for scale in scales:
            # Resize template
            width = int(template.shape[1] * scale)
            height = int(template.shape[0] * scale)
            scaled_template = cv.resize(template, (width, height))

            # Try matching at this scale
            result = self.find_template(screenshot, scaled_template, min_matches)

            if result and result[2] > best_confidence:
                best_match = result
                best_confidence = result[2]

        return best_match
