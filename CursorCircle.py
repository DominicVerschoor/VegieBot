"""Cursor overlay circle for head tracking visualization

Based on: https://github.com/JEOresearch/EyeTracker/tree/main/HeadTracker
"""
import sys
import cv2
import numpy as np
import pyautogui
from PyQt5 import QtWidgets, QtGui, QtCore

class CursorOverlay(QtWidgets.QWidget):
    """Translucent cursor overlay for head tracking feedback"""
    
    def __init__(self, radius=30):
        super().__init__()
        self.radius = radius
        self.diameter = 2 * radius + 4
        
        # Window setup
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool |
            QtCore.Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFixedSize(self.diameter, self.diameter)

        # Create label for overlay
        self.label = QtWidgets.QLabel(self)
        self.label.setGeometry(0, 0, self.diameter, self.diameter)

        # Update timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_position)
        self.timer.start(10)  # 100 FPS

    def update_position(self):
        """Update overlay position to follow mouse cursor"""
        x, y = pyautogui.position()
        self.move(x - self.radius, y - self.radius)
        self.draw_circle()

    def draw_circle(self):
        """Draw the cursor overlay circle"""
        # Create transparent image
        img = np.zeros((self.diameter, self.diameter, 4), dtype=np.uint8)

        # Draw green ring
        center = (self.radius + 2, self.radius + 2)
        cv2.circle(img, center, self.radius - 5, (0, 255, 0, 255), 10)

        # Convert to Qt pixmap
        qimg = QtGui.QImage(img.data, self.diameter, self.diameter, QtGui.QImage.Format_RGBA8888)
        pixmap = QtGui.QPixmap.fromImage(qimg)
        self.label.setPixmap(pixmap)

def main():
    """Run the cursor overlay"""
    app = QtWidgets.QApplication(sys.argv)
    overlay = CursorOverlay(radius=80)
    overlay.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
