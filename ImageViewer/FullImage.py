from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QGraphicsRectItem
from PySide6.QtGui import QPixmap, QResizeEvent, QWheelEvent, QMouseEvent, QKeyEvent, QCursor, QColor
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal

from ImageViewer.ImageInfoDialog import ImageInfoDialog
from ImageViewer.Constants import ZOOM_SCALE_FACTOR, DODGER_BLUE_50PC
import ImageViewer.ImageTools as ImageTools

class FullImage(QGraphicsView):
    # Signals to enable and disable menu items
    resetZoomEnableSignal = Signal(bool)
    rectPresentSignal = Signal(bool)
    imageModifiedSignal = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # Ensure transformations happen under the mouse position
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # Use the built in drag scrolling
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        # Create a pixmap to hold the image
        self._pixmap = QPixmap()

        # A Qt Image from pillow to contain the original image
        self._pilImage: Optional[Image.Image] = None

        # Create a graphics scene for this graphics view
        self._scene = QGraphicsScene()

        # A pixmap graphics item for the image
        self._pixmapGraphicsItem: Optional[QGraphicsPixmapItem] = None

        # A graphics rect item for the selection rectangle
        self._graphicsRectItem: Optional[QGraphicsRectItem] = None

        # Add the scene to the view
        self.setScene(self._scene)

        # Initialise zoomed to false
        self._zoomed = False

    def InitialiseView(self, imagePath:Path) -> None:
        # Set the image path
        self._imagePath = imagePath

        # Indicate whether we have zoomed in at all
        self.ResetZoom()

        # Store how much the current image is scaled
        self._currentScale: float = 1.0

        # Indicate that Control is held down
        self._ctrlHeld = False

        # A point for the start of the drag
        self._startDragPoint: Optional[QPoint] = None

        # A list containing the last n versions of this image
        self._undoBuffer: list[Image.Image] = []

        # If a graphics rect exists, remove it and set to None
        if self._graphicsRectItem is not None:
            self._scene.removeItem(self._graphicsRectItem)
            self._graphicsRectItem: Optional[QGraphicsRectItem] = None

            # Signal the menu item to be disabled
            self.rectPresentSignal.emit(False)

        # Boolean indicating whether a change to the image can be saved
        self._imageCanBeSaved = False

        # Load the image, convert it to a pixmap and add it to the scene
        self._LoadPixmap()

    def _LoadPixmap(self) -> None:
        # Use Pillow to open the image and convert to a QPixmap
        self._pilImage = Image.open(self._imagePath)

        # Convert to a QImage
        qtImage = ImageQt(self._pilImage)

        # Convert the QImage to a Pixmap
        self._pixmap.convertFromImage(qtImage)

        # If there is an old pixmap, remove it and set it to None
        if self._pixmapGraphicsItem is not None:
            self._scene.removeItem(self._pixmapGraphicsItem)
            self._pixmapGraphicsItem = None

        # Add the pixmap to the scene and return the QGraphicsPixmapItem
        self._pixmapGraphicsItem = QGraphicsPixmapItem(self._pixmap)
        self._scene.addItem(self._pixmapGraphicsItem)

        self._scene.setSceneRect(self._pixmapGraphicsItem.boundingRect())

        # Set the transformation mode to smooth for the pixmap to avoid aliasing and pixelation
        self._pixmapGraphicsItem.setTransformationMode(Qt.TransformationMode.SmoothTransformation)

        # Reset the zoom
        self.ResetZoom()

    def ZoomImage(self) -> None:
        #  Check there is a rectangle on the screen
        if self._graphicsRectItem:
            # Zoom to this rectangle, maintaining aspect ratio
            self.fitInView(self._graphicsRectItem, Qt.AspectRatioMode.KeepAspectRatio)

            # Remove the rectangle
            self._scene.removeItem(self._graphicsRectItem)

            # Set the rectangle to None
            self._graphicsRectItem = None

            # Signal the menu item to be disabled
            self.rectPresentSignal.emit(False)

            # Indicate that we are zoomed
            self._zoomed = True

            # Signal the menu item to be enabled
            self.resetZoomEnableSignal.emit(True)

    def ResetZoom(self) -> None:
        if self._pixmapGraphicsItem:
            # Reset the zoom so the whole image is visible in the window
            self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)

            # We are no longer zoomed
            self._zoomed = False

            # Signal the menu item to be disabled
            self.resetZoomEnableSignal.emit(False)

    def _updatePixmap(self) -> None:
        if self._pilImage is not None:
            if self._graphicsRectItem is not None:
                # Remove the rect if it exists
                self._scene.removeItem(self._graphicsRectItem)

                # Set the rect to None
                self._graphicsRectItem = None

            # Signal the menu item to be disabled
                self.rectPresentSignal.emit(False)
    
            # Convert the pillow image into a QImage
            qtImage = self._pilImage.toqimage()

            # Set the pixmap to this new image
            self._pixmap.convertFromImage(qtImage)

            if self._pixmapGraphicsItem is not None:
                # Remove the old pixmap from the scene
                self._scene.removeItem(self._pixmapGraphicsItem)

            # Add the new pixmap to the scene
            self._pixmapGraphicsItem = QGraphicsPixmapItem(self._pixmap)
            self._scene.addItem(self._pixmapGraphicsItem)

            # Fit the new pixmap in the view
            self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)

            # Set the scene rect to the new pixmap
            self._scene.setSceneRect(self._pixmapGraphicsItem.boundingRect())

            # Indicate that we are not zoomed
            self._zoomed = False

            # Signal the menu item to be disabled
            self.resetZoomEnableSignal.emit(False)

    def UndoLastChange(self) -> None:
        # If there are items in the buffer
        if self._undoBuffer:
            # Pop the latest image off the buffer
            self._pilImage = self._undoBuffer.pop()

            # Update the pixmap to this older image
            self._updatePixmap()

        if not self._undoBuffer:
            # If the undo buffer has been exhausted we are back to the original image so disable saving
            self._imageCanBeSaved = False

            # Signal the menu item to be disabled
            self.imageModifiedSignal.emit(False)

    def SaveImage(self) -> None:
        if self._imageCanBeSaved and self._pilImage is not None:
            # Construct the filename
            filename = self._imagePath.parent / f'{self._imagePath.stem} - Modified {datetime.now().strftime("%y-%m-%d %H.%M.%S")}.png'

            # Save the image
            self._pilImage.save(filename)

    @staticmethod
    def undo(func: Callable) -> Callable:
        def wrapper(self: FullImage, *args, **kwargs):
            if self._pilImage is not None:
                # Add the current image to the undo buffer
                self._undoBuffer.append(self._pilImage)

                # Call the manipulation function
                func(self, args, kwargs)

                # Update the pixmap
                self._updatePixmap()

                # Indicate that the image can be saved
                self._imageCanBeSaved = True

                # Signal the menu item to be enabled
                self.imageModifiedSignal.emit(True)

        return wrapper

    @undo
    def CropImage(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._graphicsRectItem is not None and self._pilImage is not None:
            # Get the rect to be cropped
            rect = self._graphicsRectItem.rect().toRect()

            # Copy the cropped area out of the QImage
            self._pilImage = self._pilImage.crop((rect.left(), rect.top(), rect.right(), rect.bottom()))

    @undo
    def Sharpen(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.Sharpen(self._pilImage)

    @undo
    def Blur(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.Blur(self._pilImage)

    @undo
    def Contour(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.Contour(self._pilImage)

    @undo
    def Detail(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.Detail(self._pilImage)

    @undo
    def EdgeEnhance(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.EdgeEnhance(self._pilImage)

    @undo
    def Emboss(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.Emboss(self._pilImage)

    @undo
    def FindEdges(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.FindEdges(self._pilImage)

    @undo
    def Smooth(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.Smooth(self._pilImage)

    @undo
    def UnsharpMask(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.UnsharpMask(self._pilImage)

    @undo
    def AutoContrast(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Update the image with the new version
            self._pilImage = ImageTools.AutoContrast(self._pilImage)

    def IncreaseColour(self) -> None:
        # Increase the colour in response to a menu selection
        self.Colour(factor = 1.1)

    def DecreaseColour(self) -> None:
        # Decrease the colour in response to a menu selection
        self.Colour(factor = 0.9)

    @undo
    def Colour(self, args: tuple[Any], kwargs: dict[str, float]) -> None:
        if self._pilImage is not None:
            self._pilImage = ImageTools.Colour(self._pilImage, kwargs.get('factor', 1.0))

    def IncreaseContrast(self) -> None:
        # Increase the contrast in response to a menu selection
        self.Contrast(factor = 1.1)

    def DecreaseContrast(self) -> None:
        # Decrease the contrast in response to a menu selection
        self.Contrast(factor = 0.9)

    @undo
    def Contrast(self, args: tuple[Any], kwargs: dict[str, float]) -> None:
        if self._pilImage is not None:
            self._pilImage = ImageTools.Contrast(self._pilImage, kwargs.get('factor', 1.0))

    def IncreaseBrightness(self) -> None:
        # Increase the brightness in response to a menu selection
        self.Brightness(factor = 1.1)

    def DecreaseBrightness(self) -> None:
        # Decrease the brightness in response to a menu selection
        self.Brightness(factor = 0.9)

    @undo
    def Brightness(self, args: tuple[Any], kwargs: dict[str, float]) -> None:
        if self._pilImage is not None:
            self._pilImage = ImageTools.Brightness(self._pilImage, kwargs.get('factor', 1.0))

    @undo
    def BlackAndWhite(self, args: tuple[Any], kwargs: dict[str, float]) -> None:
        if self._pilImage is not None:
            self._pilImage = ImageTools.Colour(self._pilImage, 0.0)

    def ImageInfo(self) -> None:
        if self._pilImage is not None:
            # Create a dictionary containing the image information
            info: dict[str, str] = {
                'Format': self._pilImage.format if self._pilImage.format is not None else '',
                'Format Description': self._pilImage.format_description if self._pilImage.format_description is not None else '',
                'Width': str(self._pilImage.width),
                'Height': str(self._pilImage.height),
                'Mode': self._pilImage.mode,
            }

            # Create a dialog to show the information
            dialog = ImageInfoDialog(self, info)

            # Show the dialog
            dialog.exec()

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)

        if not self._zoomed:
            # Ensure the image fits into the window if itis not already zoomed
            if self._pixmapGraphicsItem is not None:
                self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            # Centre on the original scene centre
            self.centerOn(self._oldSceneCentre)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)

        match event.key():
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

                # Signal the menu item to be disabled
                self.rectPresentSignal.emit(False)

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
            if self._pixmapGraphicsItem is not None:
                rect = rect.intersected(self._pixmapGraphicsItem.boundingRect())

            # Add the rect to the scene
            self._graphicsRectItem = self._scene.addRect(rect)

            # Set the outline to blue
            self._graphicsRectItem.setPen(QColor(Qt.blue))

            # Set the fill to dodger blue, 50% opaque
            self._graphicsRectItem.setBrush(DODGER_BLUE_50PC)

            # Signal the menu item to be enabled
            self.rectPresentSignal.emit(True)

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)

        if event.angleDelta().y() > 0:
            # Scale the image up by the zoom factor
            self.scale(ZOOM_SCALE_FACTOR, ZOOM_SCALE_FACTOR)

            # Show that we have zoomed
            self._zoomed = True

            # Signal the menu item to be enabled
            self.resetZoomEnableSignal.emit(True)

        elif event.angleDelta().y() < 0:
            # Scale the image down by the zoom factor
            self.scale(1 / ZOOM_SCALE_FACTOR, 1 / ZOOM_SCALE_FACTOR)

            # Show that we have zoomed
            self._zoomed = True

            # Signal the menu item to be enabled
            self.resetZoomEnableSignal.emit(True)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)

        # Get the scene coordinate of the centre of this view
        self._oldSceneCentre = self.mapToScene(self.rect().center())
