from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt

from PyQt6.QtWidgets import QLabel, QStackedWidget
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtCore import Qt

class FullImage(QLabel):
    def __init__(self, imagePath: Path, parent=None):
        super().__init__(parent=parent)

        # Set the image path
        self._imagePath = imagePath

        # Set the minimum size of this label to 1 pixel by 1 pixel
        self.setMinimumSize(1, 1)

        # Use Pillow to open the image and convert to a QPixmap
        pilImage = Image.open(imagePath)
        self._qtImage = ImageQt(pilImage)
        self._pixmap = QPixmap()

        # Align the label in the centre of the window
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)

        # Get the parent of this widget, should be a QStackedWidget
        parent = self.parent()

        # Check this is a QStackedWidget
        if isinstance(parent, QStackedWidget):
            # Convert the PIL qtImage into a QPixmap
            self._pixmap.convertFromImage(self._qtImage)

            # Scale the pixmap to the window size
            currentImage = self._pixmap.scaled(
                parent.size().width(),
                parent.size().height(),
                aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                transformMode=Qt.TransformationMode.SmoothTransformation
            )

            # Set the image to be the pixmap
            self.setPixmap(currentImage)
