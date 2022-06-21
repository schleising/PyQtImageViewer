from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt

from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class FullImage(QLabel):
    def __init__(self, imagePath: Path, parent=None):
        super().__init__(parent=parent)

        self._imagePath = imagePath

        # Use Pillow to open the image and convert to a QPixmap
        pilImage = Image.open(imagePath)
        qtImage = ImageQt(pilImage)
        pixmap = QPixmap()
        pixmap.convertFromImage(qtImage)

        # Scale the image to the thumbnail size
        if isinstance(parent, QMainWindow):
            currentImage = pixmap.scaled(parent.size().width(), parent.size().height(), aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)

            # Set the image to be the label pixmap
            self.setPixmap(currentImage)

        # Align the label in the centre of the window
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
