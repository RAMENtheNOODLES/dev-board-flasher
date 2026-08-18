# vignette_overlay.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget


class VignetteOverlay(QWidget):
    """Semi-transparent overlay shown while a file is being dragged over the window.

    Darkens the underlying window and displays a "Drop File Here" label.
    Mouse events pass through to the widgets beneath it.
    """

    def __init__(self, parent=None):
        """Initializes the overlay as hidden and transparent to mouse events.

        Args:
            parent (QWidget, optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        # Fix applied previously for WidgetAttribute
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

    def paintEvent(self, event):
        """Draws the darkened background and centered drop-target label.

        Args:
            event (QPaintEvent): The paint event triggering this redraw.
        """
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
