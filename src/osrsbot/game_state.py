import re
import os
import logging
import pytesseract

import pygetwindow as gw
import pyautogui
import pytesseract
import re
import time
from PIL import ImageEnhance, ImageOps
from collections import Counter, deque
from collections import deque as _dequ
from osrsbot.ocr_helpers import preprocess_for_shape_detection, count_holes_and_tail, looks_like_nine

from typing import Optional
from PIL import ImageEnhance, ImageOps

from osrsbot.game_interface import GameInterface
from osrsbot.config import Config

logger = logging.getLogger(__name__)

class HPDetector:
    def __init__(self, window_getter: Optional[callable] = None, window_size: int = 5):
        self.hp_history = deque(maxlen=window_size)
        self.last_valid_hp = None
        self._window_getter = window_getter

    def get_window_position(self):
        if self._window_getter is not None:
            try:
                pos = self._window_getter()
                if pos:
                    return pos
            except Exception:
                logger.exception("window_getter raised an exception")

        title = "RuneLite - 61grouphunt"
        windows = gw.getWindowsWithTitle(title)
        for app_window in windows:
            if title in app_window.title:
                return app_window.left, app_window.top, app_window.width, app_window.height
        return None

    def clean_ocr_text(self, text: str) -> str:
        replacements = {
            'i': '1', 'I': '1', 'l': '1', '|': '1',
            'o': '0', 'O': '0', 'Q': '0',
            'S': '5', 's': '5',
            'Z': '2', 'z': '2',
            'B': '8', 'g': '9', 'G': '6',
            ' ': '', '\n': '', '\r': '', '\t': '',
            'D': '0', 'd': '0', 'q': '9', 'a': '4'
        }
        cleaned = text or ""
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        return cleaned

    def preprocess_for_9_and_11(self, screenshot):
        # Multiple preprocessing strategies needed because digits 9 and 11 require
        # different contrast/threshold combinations to be distinguished from 4 and 1
        strategies = []

        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 5, img.height * 5))
        enhancer = ImageEnhance.Contrast(img)
        img1 = enhancer.enhance(4)
        img1 = img1.point(lambda p: 255 if p > 61 else 0)
        strategies.append(img1)

        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 6, img.height * 6))
        enhancer = ImageEnhance.Contrast(img)
        img2 = enhancer.enhance(3)
        img2 = img2.point(lambda p: 255 if p > 40 else 0)
        strategies.append(img2)

        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 4, img.height * 4))
        enhancer = ImageEnhance.Contrast(img)
        img3 = enhancer.enhance(3.5)
        img3 = img3.point(lambda p: 255 if p > 65 else 0)
        strategies.append(img3)

        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 5, img.height * 5))
        enhancer = ImageEnhance.Contrast(img)
        img4 = enhancer.enhance(5)
        img4 = img4.point(lambda p: 255 if p > 70 else 0)
        strategies.append(img4)

        img = screenshot.convert('L')
        img = ImageOps.invert(img)
        img = img.resize((img.width * 5, img.height * 5))
        enhancer = ImageEnhance.Contrast(img)
        img5 = enhancer.enhance(4)
        img5 = img5.point(lambda p: 255 if p > 100 else 0)
        strategies.append(img5)

        return strategies

    def get_raw_hp(self):
        window_position = self.get_window_position()
        if not window_position:
            logger.debug("get_raw_hp: no window position found")
            return None

        x, y, width, height = window_position
        hp_region = (x + 527, y + 79, 35, 20)

        screenshot = pyautogui.screenshot(region=hp_region)
        strategies = self.preprocess_for_9_and_11(screenshot)

        os.makedirs("ocr_debug", exist_ok=True)

        configs = [r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789']
        all_results = []

        for i, processed_img in enumerate(strategies):
            fname = os.path.join("ocr_debug", f"hp_strategy_{i}.png")
            try:
                processed_img.save(fname)
            except Exception:
                logger.debug(f"Failed to save debug image {fname}", exc_info=True)

            for config in configs:
                try:
                    text = pytesseract.image_to_string(processed_img, config=config)
                    cleaned_text = self.clean_ocr_text(text)
                    logger.debug(f"OCR strategy {i} -> raw:'{text.strip()}' cleaned:'{cleaned_text}'")
                    hp = re.findall(r'\d+', cleaned_text)
                    if hp:
                        hp_value = int(hp[0])
                        if 1 <= hp_value <= 99:
                            all_results.append(hp_value)
                except Exception:
                    logger.exception("Tesseract failed on processed image")

        if not all_results:
            return None

        ocr_consensus = Counter(all_results).most_common(1)[0][0]

        # OCR consistently misreads 9 as 4 due to similar closed-loop shapes
        if ocr_consensus == 4:
            try:
                nine_votes = 0
                diagnostics = []
                for idx, proc_img in enumerate(strategies):
                    try:
                        bw = preprocess_for_shape_detection(proc_img, size=(140, 140))
                        hc, tf, asp = count_holes_and_tail(bw)
                    except Exception:
                        hc, tf, asp = 0, 0.0, 0.0
                    diagnostics.append((idx, hc, tf, asp))

                    try:
                        if looks_like_nine(proc_img):
                            nine_votes += 1
                    except Exception:
                        pass

                if nine_votes > 0 or 9 in all_results:
                    logger.debug(f"4->9_check: nine_votes={nine_votes}, raw_votes_has9={9 in all_results}, per-strategy={diagnostics}")

                if nine_votes >= 2 or (nine_votes >= 1 and 9 in all_results):
                    logger.info("ðŸ”§ Correcting OCR 4 -> 9 based on multi-strategy shape heuristic")
                    ocr_consensus = 9
            except Exception:
                logger.exception("Shape-checking error")

        return ocr_consensus

    def get_smoothed_hp(self):
        raw_hp = self.get_raw_hp()
        if raw_hp is None:
            return self.last_valid_hp

        self.hp_history.append(raw_hp)
        if len(self.hp_history) >= 0:
            counter = Counter(self.hp_history)
            smoothed_hp, count = counter.most_common(1)[0]

            # Reject sudden jumps >30 HP as likely OCR errors
            if self.last_valid_hp is not None and abs(smoothed_hp - self.last_valid_hp) > 30:
                logger.warning(f"Suspicious jump: {self.last_valid_hp} -> {smoothed_hp}")
                return self.last_valid_hp

            self.last_valid_hp = smoothed_hp
            confidence = (count / len(self.hp_history)) * 100
            logger.info(f"HP: {smoothed_hp} (confidence: {confidence:.0f}%, history: {list(self.hp_history)})")
            return smoothed_hp
        else:
            self.last_valid_hp = raw_hp
            logger.debug(f"HP (building history): {raw_hp}")
            return raw_hp


class GameState:
    def __init__(self, interface: GameInterface, config: Config) -> None:
        self.interface = interface
        self.config = config

        self.hp_detector = HPDetector()
        self.hp_detector.get_window_position = self.interface.get_window_position  # type: ignore

        self._health_cache: Optional[int] = None
        self._health_time: float = 0.0

        # Cache TTL prevents expensive OCR from running on every call in tight loops
        self._hp_ttl = float(self.config.get("ocr", "hp_ttl", default=0.5))

        tesseract_path = self.config.get("tesseract_path")
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Using Tesseract from config: {tesseract_path}")
        elif os.getenv("TESSERACT_PATH"):
            pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH")
            logger.info(f"Using Tesseract from env: {os.getenv('TESSERACT_PATH')}")
        else:
            logger.info("Using default Tesseract path (system)")

    def inventory_full(self) -> bool:
        coord = self.config.get("coordinates", "inventory", "last_slot")
        if not coord:
            logger.error("last_slot coordinates not in config")
            return False

        empty_color = self.config.get("colors", "empty_slot", default=(75, 66, 58))
        color = self.interface.get_pixel(coord['x'], coord['y'])

        is_full = color != empty_color
        logger.debug(f"Inventory full check: {is_full} (slot color: {color})")
        return is_full

    def in_combat(self) -> bool:
        coord = self.config.get("coordinates", "checks", "combat_indicator")
        if not coord:
            logger.error("combat check coordinates were not found in config.")
            return False
        color = self.interface.get_pixel(coord['x'], coord['y'])

        combat_colors = [(7, 139, 54), (99, 21, 19)]
        tolerance = self.config.get("tolerances", "color_match")

        return any(
            all(abs(color[i] - cc[i]) <= tolerance for i in range(3))  # type: ignore
            for cc in combat_colors
        )

    def clean_ocr_text(self, text):
        replacements = {
            'i': '1', 'I': '1', 'l': '1', '|': '1',
            'o': '0', 'O': '0', 'Q': '0',
            'S': '5', 's': '5',
            'Z': '2', 'z': '2',
            'B': '8', 'g': '9', 'G': '6',
            ' ': '', '\n': '', '\r': '', '\t': '',
            'D': '0', 'd': '0'
        }

        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        return cleaned

    def get_hp(self, force: bool = False) -> Optional[int]:
        now = time.time()

        if not force and self._health_cache is not None and (now - self._health_time) < self._hp_ttl:
            logger.debug(f"get_hp: returning cached health {self._health_cache}")
            return self._health_cache

        if not hasattr(self.hp_detector, "get_window_position") or self.hp_detector.get_window_position is None:
            self.hp_detector.get_window_position = self.interface.get_window_position  # type: ignore

        hp = self.hp_detector.get_smoothed_hp()
        if hp is None:
            logger.debug("get_hp: HPDetector returned None (OCR failed). Keeping cache.")
            return self._health_cache

        self._health_cache = int(hp)
        self._health_time = now
        logger.debug(f"get_hp: new cached health {self._health_cache}")
        return self._health_cache
        
    