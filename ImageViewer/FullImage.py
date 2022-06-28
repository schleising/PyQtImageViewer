from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView
from PySide6.QtGui import QPixmap, QResizeEvent, QWheelEvent, QMouseEvent, QKeyEvent
from PySide6.QtCore import Qt, QPoint, Signal

from ImageViewer.Constants import ZOOM_SCALE_FACTOR

class FullImage(QGraphicsView):
    # Signal to return to browser
    returnToBrowser = Signal()

    # Signals for previous and next images
    previousImage = Signal()
    nextImage = Signal()

    def __init__(self, imagePath: Path, parent=None):
        super().__init__(parent=parent)

        # Set the image path
        self._imagePath = imagePath

        # Create a pixmap to hold the image
        self._pixmap = QPixmap()

        # Create a graphics scene for this graphics view
        self._scene = QGraphicsScene()

        # Add the scene to the view
        self.setScene(self._scene)

        # Load the image, convert it to a pixmap and add it to the scene
        self._LoadPixmap()

        # Last mouse position, used for mouse dragging
        self._lastMousePos: Optional[QPoint] = None

        # Store how much the current image is scaled
        self._currentScale: float = 1.0

    def _LoadPixmap(self) -> None:
        # Use Pillow to open the image and convert to a QPixmap
        pilImage = Image.open(self._imagePath)

        # Convert to a QImage
        self._qtImage = ImageQt(pilImage)

        # Convert the QImage to a Pixmap
        self._pixmap.convertFromImage(self._qtImage)

        # Add the pixmap to the scene
        self._scene.addPixmap(self._pixmap)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)

        # Reset the scale (as scale is cumulative)
        self.scale(1 / self._currentScale, 1 / self._currentScale)

        # Calculate the new scale
        self._currentScale = min((self.width() - 2) / self._pixmap.width(), (self.height() - 2) / self._pixmap.height())

        # Apply the new scale value
        self.scale(self._currentScale, self._currentScale)

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)

        if event.angleDelta().y() > 0:
            # Scale the image up by the zoom factor
            self.scale(ZOOM_SCALE_FACTOR, ZOOM_SCALE_FACTOR)

        elif event.angleDelta().y() < 0:
            # Scale the image down by the zoom factor
            self.scale(1 / ZOOM_SCALE_FACTOR, 1 / ZOOM_SCALE_FACTOR)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)

        # Check it is the left button which has been clicked
        if event.button() == Qt.MouseButton.LeftButton:
            # Store the click position
            self._lastMousePos = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)

        # Check it is the left mouse button which has been released
        if event.button() == Qt.MouseButton.LeftButton:
            # Clear the last mouse position
            self._lastMousePos = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)

        # Check we have a last mouse position and the left button is held
        if self._lastMousePos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            # Work out how far we've moved in x and y
            dx = event.pos().x() - self._lastMousePos.x()
            dy = event.pos().y() - self._lastMousePos.y()

            # Store the current mouse position
            self._lastMousePos = event.pos()

            # Adjust the scroll bars by the dx and dy values
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)

        if event.key() == Qt.Key.Key_Up:
            # Send the return to browser signal
            self.returnToBrowser.emit()
        elif event.key() == Qt.Key.Key_Left:
            # Send the previous image signal
            self.previousImage.emit()
        elif event.key() == Qt.Key.Key_Right:
            # Send the next image signal
            self.nextImage.emit()
