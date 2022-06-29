from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QGraphicsRectItem
from PySide6.QtGui import QPixmap, QResizeEvent, QWheelEvent, QMouseEvent, QKeyEvent, QCursor, QColor, QImage
from PySide6.QtCore import Qt, Signal, QPoint, QPointF, QRectF

from ImageViewer.Constants import ZOOM_SCALE_FACTOR, DODGER_BLUE

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

        # A Qt Image from pillow to contain the original image
        self._qtImage: Optional[QImage] = None

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

        # Set the transformation mode to smooth for the pixmap to avoid aliasing and pixelation
        self._pixmapGraphicsItem.setTransformationMode(Qt.TransformationMode.SmoothTransformation)

        # Indicate whether we have zoomed in at all
        self._zoomed = False

        # Store how much the current image is scaled
        self._currentScale: float = 1.0

        # Indicate that Control is held down
        self._ctrlHeld = False

        # A point for the start of the drag
        self._startDragPoint: Optional[QPoint] = None

        # A graphics rect item for the selection rectangle
        self._graphicsRectItem: Optional[QGraphicsRectItem] = None

        # A list containing the last n versions of this image
        self._undoBuffer: list[QImage] = []

        # Boolean indicating whether a change to the image can be saved
        self._imageCanBeSaved = False

    def _LoadPixmap(self) -> QGraphicsPixmapItem:
        # Use Pillow to open the image and convert to a QPixmap
        pilImage = Image.open(self._imagePath)

        # Convert to a QImage
        self._qtImage = ImageQt(pilImage)

        # Convert the QImage to a Pixmap
        self._pixmap.convertFromImage(self._qtImage)

        # Add the pixmap to the scene and return the QGraphicsPixmapItem
        return self._scene.addPixmap(self._pixmap)

    def ZoomImage(self) -> None:
        #  Check there is a rectangle on the screen
        if self._graphicsRectItem:
            # Zoom to this rectangle, maintaining aspect ratio
            self.fitInView(self._graphicsRectItem, Qt.AspectRatioMode.KeepAspectRatio)

            # Remove the rectangle
            self._scene.removeItem(self._graphicsRectItem)

            # Set the rectangle to None
            self._graphicsRectItem = None

            # Indicate that we are zoomed
            self._zoomed = True

    def ResetZoom(self) -> None:
        if self._zoomed and self._pixmapGraphicsItem:
            # Reset the zoom so the whol imaage is visible in the window
            self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)

            # We are no longer zoomed
            self._zoomed = False

    def _updatePixmap(self) -> None:
        if self._qtImage is not None:
            if self._graphicsRectItem is not None:
                # Remove the rect if it exists
                self._scene.removeItem(self._graphicsRectItem)

                # Set the rect to None
                self._graphicsRectItem = None

            # Set the pixmap to this new image
            self._pixmap.convertFromImage(self._qtImage)

            # Remove the old pixmap from the scene
            self._scene.removeItem(self._pixmapGraphicsItem)

            # Add the new pixmap to the scene
            self._pixmapGraphicsItem = self._scene.addPixmap(self._pixmap)

            # Fit the new pixmap in the view
            self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)

            # Set the scene rect to the new pixmap
            self._scene.setSceneRect(self._pixmapGraphicsItem.boundingRect())

            # Indicate that we are not zoomed
            self._zoomed = False

    def CropImage(self) -> None:
        if self._graphicsRectItem is not None and self._qtImage is not None:
            # Add the current QImage to the undo buffer
            self._undoBuffer.append(self._qtImage.copy())

            # Copy the cropped area out of the QImage
            self._qtImage = self._qtImage.copy(self._graphicsRectItem.rect().toRect())

            # Update the pixmap
            self._updatePixmap()

            # Indicate that the image can be saved
            self._imageCanBeSaved = True

    def UndoLastChange(self) -> None:
        # If there are items in the buffer
        if self._undoBuffer:
            # Pop the latest image off the buffer
            self._qtImage = self._undoBuffer.pop()

            # Update the pixmap to this older image
            self._updatePixmap()

        if not self._undoBuffer:
            # If the undo buffer has been exhausted we are back to the original image so disable saving
            self._imageCanBeSaved = False

    def SaveImage(self) -> None:
        if self._imageCanBeSaved and self._qtImage is not None:
            # Construct the filename
            filename = self._imagePath.parent / f'{self._imagePath.stem} - Modified {datetime.now().strftime("%y-%m-%d %H.%M.%S")}.png'

            # Save the image
            self._qtImage.save(filename.as_posix())

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)

        if not self._zoomed:
            # Ensure the image fits into the window if itis not already zoomed
            self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)

        match event.key():
            case Qt.Key.Key_Up:
                # Send the return to browser signal
                self.returnToBrowser.emit()

            case Qt.Key.Key_Meta: # In Qt Mac Control = Key_Meta, Command = Key_Control
                # Set control held to True
                self._ctrlHeld = True

                # Store the point of the start of the drag
                self._startDragPoint = self.mapFromGlobal(QCursor().pos())

                # Set the drag mode to no drag
                self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        super().keyReleaseEvent(event)

        match event.key():
            case  Qt.Key.Key_Meta: # In Qt Mac Control = Key_Meta, Command = Key_Control
                # Set control held to False
                self._ctrlHeld = False

                # Set the drag mode back to scroll hand drag
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)

        # Ignore the event if Control is held
        if not event.modifiers() & Qt.Modifier.META: # META is actually Control

            # If this is a left click and there is a rect, remove it
            if event.button() == Qt.MouseButton.LeftButton and self._graphicsRectItem is not None:
                # Remove the rect from the scene
                self._scene.removeItem(self._graphicsRectItem)

                # Set the rect to None
                self._graphicsRectItem = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)

        if self._startDragPoint is not None and self._ctrlHeld:
            if self._graphicsRectItem is not None:
                # Remove the existing graphics rect item
                self._scene.removeItem(self._graphicsRectItem)

            # Get the cursor position in scene coordinates
            sceneCursorPos = self.mapToScene(self.mapFromGlobal(QCursor().pos()))

            # Get the start drag point in scene coordinates
            sceneStartDragPoint = self.mapToScene(self._startDragPoint)

            # Get the top left point (min of both xs and ys)
            topLeft = QPointF(min(sceneStartDragPoint.x(), sceneCursorPos.x()), min(sceneStartDragPoint.y(), sceneCursorPos.y()))

            # Get the bottom left point (max of both xs and ys)
            bottomRight = QPointF(max(sceneStartDragPoint.x(), sceneCursorPos.x()), max(sceneStartDragPoint.y(), sceneCursorPos.y()))

            # Create a rect from these two points
            rect = QRectF(topLeft, bottomRight)

            # Constrain the rect to the pixmap
            rect = rect.intersected(self._pixmapGraphicsItem.boundingRect())

            # Add the rect to the scene
            self._graphicsRectItem = self._scene.addRect(rect)

            # Set the outline to blue
            self._graphicsRectItem.setPen(QColor(Qt.blue))

            # Set the fill to dodger blue, 50% opaque
            self._graphicsRectItem.setBrush(DODGER_BLUE)

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
