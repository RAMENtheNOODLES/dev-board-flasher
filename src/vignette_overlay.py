# vignette_overlay.py
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QFont

class VignetteOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Fix applied previously for WidgetAttribute
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide() 

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # FIX: Access Antialiasing explicitly through the RenderHint enum wrapper
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(55, 59, 61, 50))

		# 2. Draw the "Drop File Here" label manually on top
        painter.setPen(QColor(255, 255, 255, 220))  # White text with slight opacity
        
        font = QFont("Arial", 18, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Draw text perfectly aligned in the center of the widget bounds
        painter.drawText(
            self.rect(), 
            Qt.AlignmentFlag.AlignCenter, 
            "Drop File Here"
        )
