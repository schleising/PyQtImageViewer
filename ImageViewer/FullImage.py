from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsItem
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

        # Ensure transformations happen under the mouse position
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # Use the built in drag scrolling
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        # Add the scene to the view
        self.setScene(self._scene)

        # Load the image, convert it to a pixmap and add it to the scene
        self._pixmapGraphicsItem = self._LoadPixmap()

        # Indicate whether we have zoomed in at all
        self._zoomed = False

        # Store how much the current image is scaled
        self._currentScale: float = 1.0

        # Indicate that Control is held down
        self._ctrlHeld = False

    def _LoadPixmap(self) -> QGraphicsItem:
        # Use Pillow to open the image and convert to a QPixmap
        pilImage = Image.open(self._imagePath)

        # Convert to a QImage
        self._qtImage = ImageQt(pilImage)

        # Convert the QImage to a Pixmap
        self._pixmap.convertFromImage(self._qtImage)

        # Add the pixmap to the scene
        return self._scene.addPixmap(self._pixmap)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)

        if not self._zoomed:
            # Ensure the image fits into the window if itis not already zoomed
            self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)

        if event.angleDelta().y() > 0:
            # Scale the image up by the zoom factor
            self.scale(ZOOM_SCALE_FACTOR, ZOOM_SCALE_FACTOR)

            # Show that we have zoomed
            self._zoomed = True

        elif event.angleDelta().y() < 0:
            # Scale the image down by the zoom factor
            self.scale(1 / ZOOM_SCALE_FACTOR, 1 / ZOOM_SCALE_FACTOR)

            # Show that we have zoomed
            self._zoomed = True

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
        elif event.key() == Qt.Key.Key_Meta: # In Qt Mac Control = Key_Meta, Command = Key_Control
            # Set control held to True
            self._ctrlHeld = True

            # Set the drag mode to no drag
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        super().keyReleaseEvent(event)

        if event.key() == Qt.Key.Key_Meta: # In Qt Mac Control = Key_Meta, Command = Key_Control
            # Set control held to False
            self._ctrlHeld = False

            # Set the drag mode back to scroll hand drag
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)

        # print(event.pos().x(), event.pos().y())
