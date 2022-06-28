from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import QLabel, QScrollArea
from PySide6.QtGui import QPixmap, QResizeEvent, QWheelEvent, QMouseEvent
from PySide6.QtCore import Qt, QPoint

class FullImage(QScrollArea):
    def __init__(self, imagePath: Path, parent=None):
        super().__init__(parent=parent)

        self._label = QLabel()
        self.setMinimumSize(10,10)

        self.setWidgetResizable(True)
        self.setWidget(self._label)

        # Set the image path
        self._imagePath = imagePath

        # Set the minimum size of this label to 1 pixel by 1 pixel
        self.setMinimumSize(1, 1)

        # Use Pillow to open the image and convert to a QPixmap
        pilImage = Image.open(imagePath)
        self._qtImage = ImageQt(pilImage)
        self._pixmap = QPixmap()

        # Align the label in the centre of the window
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Used for mouse dragging
        self._lastMousePos: Optional[QPoint] = None

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)

        # Convert the PIL qtImage into a QPixmap
        self._pixmap.convertFromImage(self._qtImage)

        # Scale the pixmap to the window size
        currentImage = self._pixmap.scaled(
            self.size().width(),
            self.size().height(),
            aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
            mode=Qt.TransformationMode.SmoothTransformation
        )

        # Set the image to be the pixmap
        self._label.setPixmap(currentImage)

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)

        if event.angleDelta().y() > 0:
            currentImage = self._pixmap.scaled(int(1.1 * self._label.pixmap().size().width()), int(1.1 * self._label.pixmap().size().height()))
            self._label.setPixmap(currentImage)
        elif event.angleDelta().y() < 0:
            currentImage = self._pixmap.scaled(int(self._label.pixmap().size().width() / 1.1), int(self._label.pixmap().size().height() / 1.1))
            self._label.setPixmap(currentImage)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            print(f'Button Clicked: {event.pos()}')
            self._lastMousePos = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            print(f'Button Released')
            self._lastMousePos = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)

        if self._lastMousePos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            dx = event.pos().x() - self._lastMousePos.x()
            dy = event.pos().y() - self._lastMousePos.y()
            self._lastMousePos = event.pos()

            print(f'dx: {dx}, dy: {dy}')

            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
