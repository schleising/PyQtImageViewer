
from pathlib import Path
from typing import Optional
import logging

from PySide6.QtWidgets import QMainWindow, QScrollArea, QGridLayout, QWidget, QStackedWidget
from PySide6.QtGui import QAction, QKeyEvent, QResizeEvent, QMouseEvent, QKeySequence
from PySide6.QtCore import Qt, Signal, QTimer, QObject, QEvent

from ImageViewer.Thumbnail import Thumbnail
from ImageViewer.FullImage import FullImage
from ImageViewer.FileTypes import supportedExtensions
from ImageViewer.Constants import START_X, START_Y, START_WIDTH, START_HEIGHT, MIN_WIDTH

class MainWindow(QMainWindow):
    # Create a signal for the file open event 
    fileOpenedSignal = Signal(Path)

    """Main Window."""
    def __init__(self, parent:Optional[QWidget]=None):
        """Initializer."""
        super().__init__(parent)
        self.setWindowTitle('Python Qt Image Viewer')

        # Set up a stacked widged
        self._stack = QStackedWidget()

        # Set up a scrollable area
        self._scroll = QScrollArea()

        # Set the scroll widget to be resizable
        self._scroll.setWidgetResizable(True)

        # Install an event filter on the scroll area to get the cursor key presses
        self._scroll.installEventFilter(self)

        # Create a grid layout
        self._grid = QGridLayout()

        # Create a main widget
        self._widget = QWidget()

        # Attach the scroll area to the widget
        self._scroll.setWidget(self._widget)

        # Give the widget a grid layout
        self._widget.setLayout(self._grid)

        # Add the scollable area to the stack
        self._stack.addWidget(self._scroll)

        # Set the scroll widget to be the main widget
        self.setCentralWidget(self._stack)

        # Set the scollable widget to be the current one in the stack
        self._stack.setCurrentWidget(self._scroll)

        # Connect the file open signal to FileOpened
        self.fileOpenedSignal.connect(self.FileOpened)

        # We have not yet received a file open event
        self._fileOpenReceived = False

        # Set the numner of thumbnails per row to 8
        self._thumbnailsPerRow = 8

        # Create a thumbnail list
        self._thumbnailList: list[Thumbnail] = []

        # A list of the images in the current folder
        self._imageList: list[Path] = []

        # Index of the current image
        self._currentImageIndex = 0

        # Setup a widget for the full sized image
        self._fullSizeImage: Optional[FullImage] = None

        # Keep track of whether the image is maximised or not
        self._imageMaximised = False

        # Set the window position and size
        self.setGeometry(START_X, START_Y, START_WIDTH, START_HEIGHT)

        # Set the minimum width
        self.setMinimumWidth(MIN_WIDTH)

        # Set the default path
        self._currentPath = Path.home() / 'Pictures'

        # Set a time for 150ms to see if a file open event has happened, otherwise load the default folder
        QTimer.singleShot(150, self.StartUpTimerExpired)

        # Add a menu for previous and next images, disabled to start with
        self._addImageMenu()

        # Store up which thumbnail is highlighted
        self._currentHighlightedThumbnail = 0

        # Show the window
        self.show()

    def _addImageMenu(self):
        # Get the menubar
        self._menuBar = self.menuBar()

        # Create a Next acion to call _nextImage
        self._nextAction = QAction('Next', self)
        self._nextAction.setShortcut(Qt.Key.Key_Right)

        # Create a Next acion to call _nextImage
        self._nextAction.triggered.connect(self._nextImage) # type: ignore

        # Create a Previous acion to call _prevImage
        self._prevAction = QAction('Previous', self)
        self._prevAction.setShortcut(Qt.Key.Key_Left)

        # Create a Previous acion to call _prevImage
        self._prevAction.triggered.connect(self._prevImage) # type: ignore

        # Create the Image menu
        self._imageMenu = self._menuBar.addMenu('Image')

        # Add a zoom to rect action
        self._zoomAction = QAction('Zoom to Rect', self)
        self._zoomAction.setShortcut(Qt.Key.Key_Z)

        # Add a zoom to rect action
        self._resetZoomAction = QAction('Reset Zoom', self)
        self._resetZoomAction.setShortcut(Qt.Key.Key_R)

        # Add a crop to rect action
        self._cropAction = QAction('Crop to Rect', self)
        self._cropAction.setShortcut(Qt.Key.Key_C)

        # Add an Undo action
        self._undoAction = QAction('Undo', self)
        self._undoAction.setShortcut(QKeySequence.Undo)

        # Add a Save action
        self._saveAction = QAction('Save', self)
        self._saveAction.setShortcut(QKeySequence.Save)

        # Disable the actions for now
        self._updateMenu()

    def _updateMenu(self) -> None:
        if self._imageMaximised and self._fullSizeImage is not None:
            # Connect to the zoom function of the full sized image
            self._zoomAction.triggered.connect(self._fullSizeImage.ZoomImage) # type: ignore

            # Connect to the reset zoom function of the full sized image
            self._resetZoomAction.triggered.connect(self._fullSizeImage.ResetZoom) # type: ignore

            # Connect to the crop function of the full sized image
            self._cropAction.triggered.connect(self._fullSizeImage.CropImage) # type: ignore

            # Connect to the undo function of the full sized image
            self._undoAction.triggered.connect(self._fullSizeImage.UndoLastChange) # type: ignore

            # Connect to the save function of the full sized image
            self._saveAction.triggered.connect(self._fullSizeImage.SaveImage) # type: ignore

            # Add the actions to the Image Menu
            self._imageMenu.addAction(self._nextAction)
            self._imageMenu.addAction(self._prevAction)
            self._imageMenu.addSeparator()
            self._imageMenu.addAction(self._zoomAction)
            self._imageMenu.addAction(self._resetZoomAction)
            self._imageMenu.addAction(self._cropAction)
            self._imageMenu.addSeparator()
            self._imageMenu.addAction(self._undoAction)
            self._imageMenu.addSeparator()
            self._imageMenu.addAction(self._saveAction)
        else:
            # Remove the actions from the image menu
            self._imageMenu.removeAction(self._prevAction)
            self._imageMenu.removeAction(self._nextAction)
            self._imageMenu.removeAction(self._zoomAction)
            self._imageMenu.removeAction(self._resetZoomAction)
            self._imageMenu.removeAction(self._cropAction)
            self._imageMenu.removeAction(self._undoAction)
            self._imageMenu.removeAction(self._saveAction)

    def _GetImagePathList(self) -> list[Path]:
        # Return the list of images Paths, sorted alphabetically (case insensitive)
        return sorted([image for image in self._currentPath.iterdir() if image.suffix.lower() in supportedExtensions.values()], key=lambda x: x.name.lower())

    def _GetFolderList(self) -> list[Path]:
        # Get the list of non-hidden folders in this folder
        folderList = sorted([path for path in self._currentPath.iterdir() if path.is_dir() and not path.name.startswith('.')], key=lambda x: x.name.lower())

        # Insert the parent folder at the front of the list
        folderList.insert(0, self._currentPath.parent)

        # Return the list
        return folderList

    def SetLabels(self) -> None:
        # Remove any old items from the grid layout
        while self._grid.count():
            # Removes the item
            item = self._grid.takeAt(0)

            # Set the parent to None to ensure ot gets hidden
            item.widget().setParent(None) # type: ignore

        # Clear down the thumbnail list
        self._thumbnailList.clear()

        # Get the list of folders in this folder
        fileList = self._GetFolderList()

        # Get the list of images in this folder
        self._imageList = self._GetImagePathList()

        # Get the list of images in this folder and extend the folder list
        fileList.extend(self._imageList)

        # Calculate the thumbnail size
        thumbnailSize = (self.width() // self._thumbnailsPerRow) - 2 * self._grid.getContentsMargins()[0]

        # Initialise the default image (this should only actually happen once)
        Thumbnail.InitialiseDefaultImage(thumbnailSize)

        # Store up the number of rows added
        row: int = 0

        # Loop through the folders and images, creating a thumbnail for each
        for count, imagePath in enumerate(fileList):
            # Create the thumbnail, will only have the default or folder image for now
            thumbnail = Thumbnail(imagePath)

            # Work out the grid row and column
            row = count // self._thumbnailsPerRow
            column = count % self._thumbnailsPerRow

            # Add the thumbnail widget to the grid, aligning centrally
            self._grid.addWidget(thumbnail, row, column, alignment=Qt.AlignmentFlag.AlignCenter)

            # Append this to the list of thumbnails
            self._thumbnailList.append(thumbnail)

            # Connect the click on a thumbnail to this window
            thumbnail.clicked.connect(self.thumbnailClicked)

        if row == 0:
            # If there is only one row, align all items to the top left
            self._grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        else:
            # Otherwise align just to the top
            self._grid.setAlignment(Qt.AlignTop)

        # Scroll the view back to the top
        self._scroll.verticalScrollBar().setValue(0)

        # Highlight the first cell
        self._currentHighlightedThumbnail = 0
        self._thumbnailList[self._currentHighlightedThumbnail].highlighted = True

    def thumbnailClicked(self) -> None:
        # Get the widget that was clicked
        thumbnail = self.sender()

        # Get the widget is actually a thumbnail
        if isinstance(thumbnail, Thumbnail):
            # if this widget represents a folder, update the path and load the new set of thumbnails
            self.OpenItem(thumbnail.ImagePath)

    def OpenItem(self, path: Path) -> None:
        if path.is_dir():
            # Update the path
            self._currentPath = path

            # Clear and recreate the grid for this folder
            self.SetLabels()
        else:
            self.ShowImage(path)

    def FileOpened(self, imagePath: Path) -> None:
        # Show that ab file has been opened
        self._fileOpenReceived = True

        # Log that the signal has been received
        logging.log(logging.INFO, f'Wnd: File Open Signal Received: {imagePath}')

        # Set the current path to the parent of this one
        self._currentPath = imagePath.parent

        # Initialise the file browser to the parent path
        self.SetLabels()

        # Show the selected image maximised
        self.ShowImage(imagePath)

    def StartUpTimerExpired(self) -> None:
        # Log the the timeout has expired
        logging.log(logging.INFO, 'Wnd: Startup timeout expired')

        # If we haven't already received a file open event
        if not self._fileOpenReceived:
            # Load the browser at the default location
            self.SetLabels()

    def ShowImage(self, imagePath: Path) -> None:
        # Maximise the selected image
        self._MaximiseImage(imagePath)

        # Get the index of this image in the image list
        self._currentImageIndex = self._imageList.index(imagePath)

    def _MaximiseImage(self, imagePath: Path) -> None:
        if self._imageMaximised and self._fullSizeImage:
            # Remove the maximised image from the stack
            self._stack.removeWidget(self._fullSizeImage)

        # Create a label with just the filename for now
        self._fullSizeImage = FullImage(imagePath)

        # Connect the signals
        self._fullSizeImage.returnToBrowser.connect(self._returnToBrowser)
        self._fullSizeImage.previousImage.connect(self._prevImage)
        self._fullSizeImage.nextImage.connect(self._nextImage)

        # Add this widget to the stack
        self._stack.addWidget(self._fullSizeImage)

        # Swap the stack to this widget
        self._stack.setCurrentWidget(self._fullSizeImage)

        # Log that we are in maximaised image mode
        self._imageMaximised = True

        # Enable the previous and next image actions
        self._updateMenu()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # Check that this is a key press
        if event.type() == QEvent.KeyPress:
            # This is as much for the type checker as anything else...
            if isinstance(event, QKeyEvent):
                # Process the event
                self.keyPressEvent(event)

                # Return True to indicate that the event is accepted
                return True
            else:
                # Should never reach here
                return False
        else:
            # We haven't dealt with the event so return False
            return False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        match event.key():
            case Qt.Key.Key_Escape:
                # Close application on Escape
                self.close()

        if self._imageMaximised:
            # If the image is maximised use the image key press handler
            self._ImageKeyEvent(event)
        else:
            # Otherwise use the file browser key press handler
            self._FileBrowserKeyEvent(event)

    def _FileBrowserKeyEvent(self, event: QKeyEvent) -> None:
        match event.key():
            case Qt.Key.Key_Left:
                # Remove the highlight from the current thumbnail
                self._thumbnailList[self._currentHighlightedThumbnail].highlighted = False

                # Decrement the current thumbnail number
                self._currentHighlightedThumbnail -= 1

                # Bounds check
                if self._currentHighlightedThumbnail < 0:
                    self._currentHighlightedThumbnail = 0

                # Highlight the new thumbnail
                self._thumbnailList[self._currentHighlightedThumbnail].highlighted = True

                # Ensure the thumbnail is in view
                self._scroll.ensureWidgetVisible(self._thumbnailList[self._currentHighlightedThumbnail])

            case Qt.Key.Key_Right:
                # Remove the highlight from the current thumbnail
                self._thumbnailList[self._currentHighlightedThumbnail].highlighted = False

                # Increment the current thumbnail number
                self._currentHighlightedThumbnail += 1

                # Bounds check
                if self._currentHighlightedThumbnail >= len(self._thumbnailList):
                    self._currentHighlightedThumbnail = len(self._thumbnailList) - 1

                # Highlight the new thumbnail
                self._thumbnailList[self._currentHighlightedThumbnail].highlighted = True

                # Ensure the thumbnail is in view
                self._scroll.ensureWidgetVisible(self._thumbnailList[self._currentHighlightedThumbnail])

            case Qt.Key.Key_Up:
                # Remove the highlight from the current thumbnail
                self._thumbnailList[self._currentHighlightedThumbnail].highlighted = False

                # Decrement the current thumbnail number by the thumbnails in a row
                self._currentHighlightedThumbnail -= self._thumbnailsPerRow

                # Bounds check
                if self._currentHighlightedThumbnail < 0:
                    self._currentHighlightedThumbnail = 0

                # Highlight the new thumbnail
                self._thumbnailList[self._currentHighlightedThumbnail].highlighted = True

                # Ensure the thumbnail is in view
                self._scroll.ensureWidgetVisible(self._thumbnailList[self._currentHighlightedThumbnail])

            case Qt.Key.Key_Down:
                # Remove the highlight from the current thumbnail
                self._thumbnailList[self._currentHighlightedThumbnail].highlighted = False

                # Increment the current thumbnail number
                self._currentHighlightedThumbnail += self._thumbnailsPerRow

                # Bounds check
                if self._currentHighlightedThumbnail >= len(self._thumbnailList):
                    self._currentHighlightedThumbnail = len(self._thumbnailList) - 1

                # Highlight the new thumbnail
                self._thumbnailList[self._currentHighlightedThumbnail].highlighted = True

                # Ensure the thumbnail is in view
                self._scroll.ensureWidgetVisible(self._thumbnailList[self._currentHighlightedThumbnail])

            case Qt.Key.Key_Return:
                # Show the highlighted image (or open the folder)
                self.OpenItem(self._thumbnailList[self._currentHighlightedThumbnail].ImagePath)

    def _ImageKeyEvent(self, event: QKeyEvent) -> None:
        pass

    def _returnToBrowser(self) -> None:
        # Reset the stack back to the scroll widget
        self._stack.setCurrentWidget(self._scroll)

        if self._fullSizeImage:
            # Remove the maximised image from the stack
            self._stack.removeWidget(self._fullSizeImage)

        # Indicate that the image is no longer maximised
        self._imageMaximised = False

        # Disable the previous and next image actions
        self._updateMenu()

    def _nextImage(self) -> None:
        # Increment the current image index
        self._currentImageIndex += 1

        # Check bounds
        if self._currentImageIndex >= len(self._imageList):
            self._currentImageIndex = 0
        
        # Load the new image
        self._MaximiseImage(self._imageList[self._currentImageIndex])

    def _prevImage(self) -> None:
        # Increment the current image index
        self._currentImageIndex -= 1

        # Check bounds
        if self._currentImageIndex < 0:
            self._currentImageIndex = len(self._imageList) - 1
        
        # Load the new image
        self._MaximiseImage(self._imageList[self._currentImageIndex])

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)

        # Calculate the thumbnail size
        thumbnailSize = (self.width() // self._thumbnailsPerRow) - 2 * self._grid.getContentsMargins()[0]

        # Set the new thumbnail size
        Thumbnail.UpdateThumbnailSize(thumbnailSize)

        for thumbnail in self._thumbnailList:
            # Resize each of the thumbnails
            thumbnail.ResizeImage()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        super().mouseDoubleClickEvent(event)

        if self._imageMaximised:
            # If we are showing a full image, allow double click to toggle full screen or normal
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()