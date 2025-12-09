import sys
import time
import cv2 as cv
import numpy as np
import pygetwindow as gw
import mss
import pyautogui
from PyQt5 import QtWidgets, QtGui, QtCore

# ---------------- CONFIG ----------------
WINDOW_TITLE = "RuneLite - 61grouphunt"
FPS = 10
PADDING = 4

# ---------------- UI ELEMENTS ----------------
class UIElement:
    """Single clickable rectangle with screen offset awareness"""
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.offset_x = 0
        self.offset_y = 0

    @property
    def center_x(self):
        return self.x0 + (self.x1 - self.x0) // 2 + self.offset_x

    @property
    def center_y(self):
        return self.y0 + (self.y1 - self.y0) // 2 + self.offset_y

    def click(self):
        pyautogui.click(self.center_x, self.center_y)

# ---------------- GRID / ROW ----------------
class UIElementRow:
    """Row or grid of UI elements detected via template"""
    def __init__(self, template_path, threshold=0.68, num_cols=1, num_rows=1, sticky=False):
        self.template = cv.imread(template_path, cv.IMREAD_GRAYSCALE)
        if self.template is None:
            raise FileNotFoundError(f"Template not found: {template_path}")
        self.threshold = threshold
        self.num_cols = num_cols
        self.num_rows = num_rows
        self.elements = []
        self.detected_bbox = None
        self.visible = False
        self.last_detect_time = 0
        self.grace_period = 3.0  # Long grace period to prevent flicker
        self.sticky = sticky
        self.last_check = 0
        self.check_interval = 0.5  # Check every 0.5 seconds in sticky mode

    def detect(self, img_gray):
        # Always stay visible once detected
        if self.visible:
            return True

        res = cv.matchTemplate(img_gray, self.template, cv.TM_CCOEFF_NORMED)
        loc = np.where(res >= self.threshold)

        if len(loc[0]) == 0:
            return False

        x, y = loc[1][0], loc[0][0]
        w, h = self.template.shape[::-1]

        self.detected_bbox = (x, y, w, h)

        # subdivide into cells
        cell_w = w / self.num_cols
        cell_h = h / self.num_rows
        self.elements = []
        for r in range(self.num_rows):
            for c in range(self.num_cols):
                x0 = int(x + c * cell_w + PADDING)
                y0 = int(y + r * cell_h + PADDING)
                x1 = int(x + (c + 1) * cell_w - PADDING)
                y1 = int(y + (r + 1) * cell_h - PADDING)
                self.elements.append(UIElement(x0, y0, x1, y1))

        self.visible = True
        return True

# ---------------- SINGLE BUTTON ----------------
class UISingleButton:
    """Single UI element detected via template"""
    def __init__(self, template_path, threshold=0.68):
        self.template = cv.imread(template_path, cv.IMREAD_GRAYSCALE)
        if self.template is None:
            raise FileNotFoundError(f"Template not found: {template_path}")
        self.threshold = threshold
        self.element = None
        self.visible = False

    def detect(self, img_gray):
        # Always stay visible once detected
        if self.visible:
            return True

        res = cv.matchTemplate(img_gray, self.template, cv.TM_CCOEFF_NORMED)
        loc = np.where(res >= self.threshold)

        if len(loc[0]) == 0:
            return False

        x, y = loc[1][0], loc[0][0]
        w, h = self.template.shape[::-1]
        self.element = UIElement(x, y, x + w, y + h)
        self.visible = True
        return True

# ---------------- OVERLAY ----------------
class Overlay(QtWidgets.QWidget):
    def __init__(self, elements_list):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool |
            QtCore.Qt.WindowTransparentForInput
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.elements_list = elements_list

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_overlay)
        self.timer.start(int(1000 / FPS))

    def update_overlay(self):
        wins = gw.getWindowsWithTitle(WINDOW_TITLE)
        if not wins:
            return
        win = wins[0]
        left, top, width, height = win.left, win.top, win.width, win.height
        if width == 0 or height == 0:
            return

        self.setGeometry(left, top, width, height)

        # Capture window
        with mss.mss() as sct:
            monitor = {"left": left, "top": top, "width": width, "height": height}
            sct_img = sct.grab(monitor)
            img = np.array(sct_img)[:, :, :3]
            img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

        for item in self.elements_list:
            item.detect(img_gray)

            # update offsets
            if isinstance(item, UIElementRow):
                for e in item.elements:
                    e.offset_x = left
                    e.offset_y = top
            elif isinstance(item, UISingleButton):
                if item.element:
                    item.element.offset_x = left
                    item.element.offset_y = top

        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen(QtGui.QColor(0, 128, 255, 200))
        pen.setWidth(2)
        painter.setPen(pen)
        brush = QtGui.QBrush(QtGui.QColor(0, 128, 255, 64))
        painter.setBrush(brush)

        for item in self.elements_list:
            if isinstance(item, UIElementRow) and item.visible:
                for e in item.elements:
                    painter.drawRect(e.x0, e.y0, e.x1 - e.x0, e.y1 - e.y0)
            elif isinstance(item, UISingleButton) and item.visible:
                e = item.element
                painter.drawRect(e.x0, e.y0, e.x1 - e.x0, e.y1 - e.y0)

# ---------------- EXAMPLE USAGE ----------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    top_row = UIElementRow(r"C:\Users\ellio\Documents\Projects\workingon\top_row.png", num_cols=7)
    inventory = UIElementRow(r"C:\Users\ellio\Documents\Projects\workingon\inv_tile.png", num_cols=4, num_rows=7, sticky=True)
    bottom_row = UIElementRow(r"C:\Users\ellio\Documents\Projects\workingon\bottom_row.png", num_cols=7)
    prayer = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\special_button.png")
    stamina = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\stamina.png")
    health = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\health.png")
    special_attack = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\special_attack.png")
    golden_stamina = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\stamina_yellow.png")
    logout = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\logout.png")
    helmet = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\helmet.png")
    amulet = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\amulet.png")
    arrows = UISingleButton(r"C:\Users\ellio\Documents\Projects\workingon\arrows.png")
    
    overlay = Overlay([top_row, inventory, bottom_row, prayer, health, stamina, special_attack, golden_stamina, logout, helmet, amulet, arrows])
    overlay.show()

    # Click all detected elements once after 2s
    def click_all_once():
        for item in [prayer]:
            if isinstance(item, UIElementRow) and item.visible:
                for e in item.elements:
                    e.click()
            elif isinstance(item, UISingleButton) and item.visible:
                item.element.click()

    QtCore.QTimer.singleShot(2000, click_all_once)

    sys.exit(app.exec_())
