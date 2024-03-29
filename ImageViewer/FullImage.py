from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsSceneMouseEvent,
)
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QPixmap, QResizeEvent, QWheelEvent, QMouseEvent, QKeyEvent, QCursor, QColor
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, Signal, QLineF, QTimer, QObject

from ImageViewer.ImageInfoDialog import ImageInfoDialog
from ImageViewer.Constants import (
    ZOOM_SCALE_FACTOR,
    DODGER_BLUE_50PC,
    IMAGE_EXTENSIONS,
    VIDEO_SKIP_AMOUNT,
    AUDIO_ADJUST_AMOUNT,
    VIDEO_UI_MARGIN,
    VIDEO_POSITION_LINE_SIZE,
    VIDEO_UI_TIMEOUT,
)
import ImageViewer.ImageTools as ImageTools
from ImageViewer.SliderDialog import SliderDialog

class PolygonSignaller(QObject):
    durationJumpSignal = Signal(float)

class DurationPolygonItem(QGraphicsPolygonItem):
    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(parent)
        self.signaller = PolygonSignaller()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mousePressEvent(event)

        # Check the left button was pressed
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate the minimum x of the bounding rect
            minX = self.boundingRect().left()

            # Get the width of the bounding rect
            width = self.boundingRect().width()

            # Work out the xpos within the duration bar
            xPos = event.buttonDownPos(Qt.MouseButton.LeftButton).x() - minX

            # Work out how far through the duration bar this is
            percentage = xPos / width

            # Send the duration jump signal
            self.signaller.durationJumpSignal.emit(percentage)

class FullImage(QGraphicsView):
    # Signals to enable and disable menu items
    resetZoomEnableSignal = Signal(bool)
    canZoomToRectSignal = Signal(bool)
    canCropToRectSignal = Signal(bool)
    imageModifiedSignal = Signal(bool)
    imageLoadedSignal = Signal(bool)
    videoLoadedSignal = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # Ensure transformations happen under the mouse position
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Use the built in drag scrolling
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        # Create a pixmap to hold the image
        self._pixmap = QPixmap()

        # A Qt Image from pillow to contain the original image
        self._pilImage: Optional[Image.Image] = None

        # A temporary image for use when adjusting colour, contrast and brightness
        self._adjustedImage: Optional[Image.Image] = None

        # Create a graphics scene for this graphics view
        self._scene = QGraphicsScene()

        # A pixmap graphics item for the image
        self._pixmapGraphicsItem: Optional[QGraphicsPixmapItem] = None

        # A Graphics Video Item for videos
        self._graphicsVideoItem: Optional[QGraphicsVideoItem] = None

        # The media player for video
        self._mediaPlayer = QMediaPlayer()

        # Connect the media player position changed signal
        self._mediaPlayer.positionChanged.connect(self.VideoPositionChanged) # type: ignore

        # Create a polygon item for the video duration
        self._durationGraphicsPolygonItem: Optional[DurationPolygonItem] = None

        # Create a line item for the video position
        self._positionGraphicsLineItem: Optional[QGraphicsLineItem] = None

        # The video length
        self._videoLength = 0

        # The current time through the video
        self._currentPosition = 0

        # Timer to hide the video UI
        self._videoUiTimer: Optional[QTimer] = None

        # Audio output for video
        self._audioOutput = QAudioOutput()

        # Set the audio output for the media player
        self._mediaPlayer.setAudioOutput(self._audioOutput)

        # A graphics rect item for the selection rectangle
        self._graphicsRectItem: Optional[QGraphicsRectItem] = None

        # Add the scene to the view
        self.setScene(self._scene)

        # Initialise zoomed to false
        self._zoomed = False

    def InitialiseView(self, imagePath:Path) -> None:
        # Set the image path
        self._imagePath = imagePath

        # Stop any playing media
        self._mediaPlayer.stop()

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

        # If there is an old pixmap, remove it and set it to None
        if self._pixmapGraphicsItem is not None:
            self._scene.removeItem(self._pixmapGraphicsItem)
            self._pixmapGraphicsItem = None

        # If there is an old Graphic Video Item, remove it and set it to None
        if self._graphicsVideoItem is not None:
            self._scene.removeItem(self._graphicsVideoItem)
            self._graphicsVideoItem = None

        # If there is a duration polygon item remove it and set it to None
        if self._durationGraphicsPolygonItem is not None:
            self._scene.removeItem(self._durationGraphicsPolygonItem)
            self._durationGraphicsPolygonItem = None

        # If there is a position line item remove it and set it to None
        if self._positionGraphicsLineItem is not None:
            self._scene.removeItem(self._positionGraphicsLineItem)
            self._positionGraphicsLineItem = None

        # Reset the video length
        self._videoLength = 0

        # Reset the current position
        self._currentPosition = 0

        # Clear the Video UI Timer
        if self._videoUiTimer is not None:
            self._videoUiTimer.stop()
            self._videoUiTimer = None

        # If a graphics rect exists, remove it and set to None
        if self._graphicsRectItem is not None:
            self._scene.removeItem(self._graphicsRectItem)
            self._graphicsRectItem: Optional[QGraphicsRectItem] = None

            # Signal the menu item to be disabled
            self.canZoomToRectSignal.emit(False)
            self.canCropToRectSignal.emit(False)

        # Boolean indicating whether a change to the image can be saved
        self._imageCanBeSaved = False

        if self._imagePath.suffix in IMAGE_EXTENSIONS.values():
            # Load the image, convert it to a pixmap and add it to the scene
            self._LoadPixmap()
        else:
            # Load the video and add it to the scene
            self._LoadVideo()

    def _LoadPixmap(self) -> None:
        # Use Pillow to open the image and convert to a QPixmap
        self._pilImage = Image.open(self._imagePath)

        # Convert to a QImage
        qtImage = ImageQt(self._pilImage)

        # Convert the QImage to a Pixmap
        self._pixmap.convertFromImage(qtImage)

        # Get the QGraphicsPixmapItem
        self._pixmapGraphicsItem = QGraphicsPixmapItem(self._pixmap)

        # Add the pixmap graphics item to the scene
        self._scene.addItem(self._pixmapGraphicsItem)

        # Set the scene rect to the bounding rect of the pixmap
        self._scene.setSceneRect(self._pixmapGraphicsItem.boundingRect())

        # Reset the zoom
        self.ResetZoom()

        # Signal that an image has been loaded
        self.imageLoadedSignal.emit(True)

        # Signal that a video is not loaded
        self.videoLoadedSignal.emit(False)

    def _LoadVideo(self) -> None:
        # Create the graphics video item
        self._graphicsVideoItem = QGraphicsVideoItem()

        # Set the output of the media player to be the graphics video item
        self._mediaPlayer.setVideoOutput(self._graphicsVideoItem)

        # Add the graphics video item to the scene
        self._scene.addItem(self._graphicsVideoItem)

        # Set the source file for the media player
        self._mediaPlayer.setSource(self._imagePath.as_posix())

        # Set the media player to loop infinitely
        self._mediaPlayer.setLoops(QMediaPlayer.Loops.Infinite)

        # Connect the native size changed signal
        self._graphicsVideoItem.nativeSizeChanged.connect(self._videoSizeChanged)  # type: ignore

        # Create the video UI Timer
        self._videoUiTimer = QTimer()

        # Connect the timeout signal to _videoUiTimerExpired
        self._videoUiTimer.timeout.connect(self._videoUiTimerExpired) # type: ignore

        # Play the video
        self._mediaPlayer.play()

        # Signal that an image has not been loaded
        self.imageLoadedSignal.emit(False)

        # Signal that a video is loaded
        self.videoLoadedSignal.emit(True)

    def _videoSizeChanged(self) -> None:
        if self._graphicsVideoItem is not None and self._videoUiTimer is not None:
            # Now the size is known, set the scene rect
            self._scene.setSceneRect(self._graphicsVideoItem.boundingRect())

            # Reset the zoom to this rect
            self.ResetZoom()

            # Start the timer
            self._videoUiTimer.start(VIDEO_UI_TIMEOUT)

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
            self.canZoomToRectSignal.emit(False)
            self.canCropToRectSignal.emit(False)

            # Indicate that we are zoomed
            self._zoomed = True

            # Signal the menu item to be enabled
            self.resetZoomEnableSignal.emit(True)

    def ResetZoom(self) -> None:
        if self._pixmapGraphicsItem:
            # Reset the zoom so the whole image is visible in the window
            self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)

        elif self._graphicsVideoItem:
            # Reset the zoom so the whole image is visible in the window
            self.fitInView(self._graphicsVideoItem, Qt.AspectRatioMode.KeepAspectRatio)

        # We are no longer zoomed
        self._zoomed = False

        # Signal the menu item to be disabled
        self.resetZoomEnableSignal.emit(False)

    def UpdatePixmap(self, adjstedImage: Optional[Image.Image] = None) -> None:
        if self._pilImage is not None:
            if self._graphicsRectItem is not None:
                # Remove the rect if it exists
                self._scene.removeItem(self._graphicsRectItem)

                # Set the rect to None
                self._graphicsRectItem = None

                # Signal the menu item to be disabled
                self.canZoomToRectSignal.emit(False)
                self.canCropToRectSignal.emit(False)
    
            # Convert the pillow image into a QImage
            if adjstedImage is None:
                qtImage = self._pilImage.toqimage()
            else:
                qtImage = adjstedImage.toqimage()

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
            self.UpdatePixmap()

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
        def wrapper(self: FullImage, *args:tuple[Any], **kwargs: dict[str, Any]):
            if self._pilImage is not None:
                # Add the current image to the undo buffer
                self._undoBuffer.append(self._pilImage)

                # Call the manipulation function
                func(self, args, kwargs)

                # Update the pixmap
                self.UpdatePixmap()

                # Indicate that the image can be saved
                self._imageCanBeSaved = True

                # Signal the menu item to be enabled
                self.imageModifiedSignal.emit(True)

        return wrapper

    @undo
    def UpdateImage(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        # Set the PIL image to the adjusted image storing the last PIL image in the undo buffer
        self._pilImage = self._adjustedImage

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

    @undo
    def Denoise(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Denoise the image
            self._pilImage = ImageTools.Denoise(self._pilImage)

    @undo
    def SuperResolution(self, args: tuple[Any], kwargs: dict[str, Any]) -> None:
        if self._pilImage is not None:
            # Upscale the image 4x
            self._pilImage = ImageTools.SuperResolution(self._pilImage, 4)

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

    def _openAdjustDialog(self) -> None:
        # Create the slider dialog sending in the slots for change, accept and cancel
        sliderDialog = SliderDialog(self.SliderChanged, self.SliderChangeAccepted, self.SliderChangeRejected)

        # Open the dialog
        sliderDialog.exec()

    def SliderChanged(self, colour: float, contrast: float, brightness: float) -> None:
        if self._pilImage is not None:
            # Adjust the colour in response to a menu selection without adding it to the undo buffer
            self._adjustedImage = ImageTools.Colour(self._pilImage, colour)
            self._adjustedImage = ImageTools.Contrast(self._adjustedImage, contrast)
            self._adjustedImage = ImageTools.Brightness(self._adjustedImage, brightness)

            # Update the pixmap
            self.UpdatePixmap(self._adjustedImage)

    def SliderChangeAccepted(self) -> None:
        # If the change is accepted, update the image and undo buffer
        self.UpdateImage()

    def SliderChangeRejected(self) -> None:
        # If the chane is not accepted, set the image back to the original bypassing the undo buffer
        self.UpdatePixmap(self._pilImage)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)

        if not self._zoomed:
            # Ensure the image or video fits into the window if it is not already zoomed
            if self._pixmapGraphicsItem is not None:
                self.fitInView(self._pixmapGraphicsItem, Qt.AspectRatioMode.KeepAspectRatio)
            elif self._graphicsVideoItem is not None:
                self.fitInView(self._graphicsVideoItem, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            # Centre on the original scene centre
            self.centerOn(self._oldSceneCentre)

        # Redraw the video UI
        self._drawVideoUi()

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
        if not event.modifiers() & Qt.KeyboardModifier.MetaModifier: # META is actually Control

            # If this is a left click and there is a rect, remove it
            if event.button() == Qt.MouseButton.LeftButton and self._graphicsRectItem is not None:
                # Remove the rect from the scene
                self._scene.removeItem(self._graphicsRectItem)

                # Set the rect to None
                self._graphicsRectItem = None

                # Signal the menu item to be disabled
                self.canZoomToRectSignal.emit(False)
                self.canCropToRectSignal.emit(False)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)

        if self._durationGraphicsPolygonItem is not None and self._positionGraphicsLineItem is not None and self._videoUiTimer is not None:
            # Show the duration polygon
            self._durationGraphicsPolygonItem.show()

            # show the position line
            self._positionGraphicsLineItem.show()

            # Start the timer
            self._videoUiTimer.start(VIDEO_UI_TIMEOUT)

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
            self._graphicsRectItem.setPen(QColor(Qt.GlobalColor.blue))

            # Set the fill to dodger blue, 50% opaque
            self._graphicsRectItem.setBrush(DODGER_BLUE_50PC)

            # Signal the menu item to be enabled
            self.canZoomToRectSignal.emit(True)

            # Only enable crop for images
            if self._pixmapGraphicsItem is not None:
                self.canCropToRectSignal.emit(True)
            else:
                self.canCropToRectSignal.emit(False)

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

    def ReturnToBrowser(self) -> None:
        # Stop the video
        self._mediaPlayer.stop()

    def PlayPause(self) -> None:
        if self._mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            # If the video is playing, pause it
            self._mediaPlayer.pause()
        elif self._mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            # If the video is paused, play it
            self._mediaPlayer.play()

    def SkipForwards(self) -> None:
        # Jump ahead by the skip amount
        self._mediaPlayer.setPosition(self._mediaPlayer.position() + VIDEO_SKIP_AMOUNT)

        if self._durationGraphicsPolygonItem is not None and self._positionGraphicsLineItem is not None and self._videoUiTimer is not None:
            # Show the duration polygon
            self._durationGraphicsPolygonItem.show()

            # show the position line
            self._positionGraphicsLineItem.show()

            # Start the timer
            self._videoUiTimer.start(VIDEO_UI_TIMEOUT)

    def SkipBackwards(self) -> None:
        # Jump back by the skip amount
        self._mediaPlayer.setPosition(self._mediaPlayer.position() - VIDEO_SKIP_AMOUNT)

        if self._durationGraphicsPolygonItem is not None and self._positionGraphicsLineItem is not None and self._videoUiTimer is not None:
            # Show the duration polygon
            self._durationGraphicsPolygonItem.show()

            # show the position line
            self._positionGraphicsLineItem.show()

            # Start the timer
            self._videoUiTimer.start(VIDEO_UI_TIMEOUT)

    def _positionJump(self, newPosition: float) -> None:
        # Jump to the new position
        self._mediaPlayer.setPosition(int(self._mediaPlayer.duration() * newPosition))

    def IncreaseVolume(self) -> None:
        # Increase the volume by the adjust amount (clamped to 0 - 1)
        self._audioOutput.setVolume(self._audioOutput.volume() + AUDIO_ADJUST_AMOUNT)

        # Re-enable audio if muted
        self._audioOutput.setMuted(False)

    def DecreaseVolume(self) -> None:
        # Decrease the volume by the adjust amount (clamped to 0 - 1)
        self._audioOutput.setVolume(self._audioOutput.volume() - AUDIO_ADJUST_AMOUNT)

        # Re-enable audio if muted
        self._audioOutput.setMuted(False)

    def ToggleMute(self) -> None:
        # Toggle the muted state
        self._audioOutput.setMuted(not self._audioOutput.isMuted())

    def VideoPositionChanged(self) -> None:
        if self._durationGraphicsPolygonItem is None:
            # Create the duration polygon and add it to the scene
            self._durationGraphicsPolygonItem = DurationPolygonItem()
            self._scene.addItem(self._durationGraphicsPolygonItem)

            # Connect the duration jump signal
            self._durationGraphicsPolygonItem.signaller.durationJumpSignal.connect(self._positionJump)

        if self._positionGraphicsLineItem is None:
            # Create the position line and add it to the scene
            self._positionGraphicsLineItem = QGraphicsLineItem()
            self._scene.addItem(self._positionGraphicsLineItem)

        # Get the video length
        self._videoLength = self._mediaPlayer.duration()

        # Get the current position
        self._currentPosition = self._mediaPlayer.position()

        # Draw the UI
        self._drawVideoUi()

    def _drawVideoUi(self) -> None:
        if self._durationGraphicsPolygonItem is not None and self._positionGraphicsLineItem is not None and self._videoLength > 0:
            # Get the x start position of the duration rect in view coordinates
            durationXStart = VIDEO_UI_MARGIN

            # Get the x end position of the duration rect in view coordinates
            durationWidth = self.width() - VIDEO_UI_MARGIN - durationXStart

            # Get the y position of the duration rect in view coordinates
            durationYStart = self.height() - VIDEO_UI_MARGIN - VIDEO_POSITION_LINE_SIZE

            # Get the y position of the duration rect in view coordinates
            durationHeight = self.height() - VIDEO_UI_MARGIN + VIDEO_POSITION_LINE_SIZE - durationYStart

            # Create the duration rect in view coordinates
            durationViewRect = QRect(durationXStart, durationYStart, durationWidth, durationHeight)

            # Map the duration rect to scene coordinates, results in a polygon
            durationScenePolygon = self.mapToScene(durationViewRect)

            # Get the x position of the position line
            positionXPos = int((durationWidth * (self._currentPosition / self._videoLength)) + durationXStart)

            # Get the starting y position of the position line, plus 1 to account for no polygon outline
            positionYStart = durationYStart + 1

            # Get the ending y position of the position line, plus 1 to account for no polygon outline
            positionYEnd = positionYStart + VIDEO_POSITION_LINE_SIZE + 1

            # Create the position start and end points in view coordinations
            positionStartPoint = QPoint(positionXPos, positionYStart)
            positionEndPoint = QPoint(positionXPos, positionYEnd)

            # Create the position start and end points in scene coordinations
            scenePositionStartPoint = self.mapToScene(positionStartPoint)
            scenePositionEndPoint = self.mapToScene(positionEndPoint)

            # Create the position line
            positionLine = QLineF(scenePositionStartPoint, scenePositionEndPoint)

            # Set the duration graphics polygon item
            self._durationGraphicsPolygonItem.setPolygon(durationScenePolygon)

            # Set the border to transparent
            self._durationGraphicsPolygonItem.setPen(Qt.PenStyle.NoPen)

            # Set the fill to dodger blue
            self._durationGraphicsPolygonItem.setBrush(DODGER_BLUE_50PC)

            # Set the position graphics line item
            self._positionGraphicsLineItem.setLine(positionLine)

            # Set the line to white
            self._positionGraphicsLineItem.setPen(QColor(Qt.GlobalColor.white))

    def _videoUiTimerExpired(self) -> None:
        if self._durationGraphicsPolygonItem is not None and self._positionGraphicsLineItem is not None and self._videoUiTimer is not None:
            # Hide the video UI
            self._durationGraphicsPolygonItem.hide()
            self._positionGraphicsLineItem.hide()

            # Stop the timer to ensure it doesn't fire again
            self._videoUiTimer.stop()
