
from pathlib import Path
from typing import Optional
import logging

from PySide6.QtWidgets import QMainWindow, QScrollArea, QGridLayout, QWidget, QLabel, QStackedWidget, QMenu
from PySide6.QtGui import QAction, QKeyEvent, QResizeEvent
from PySide6.QtCore import Qt, Signal, QTimer

from ImageViewer.Thumbnail import Thumbnail
from ImageViewer.FullImage import FullImage
from ImageViewer.FileTypes import supportedExtensions

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
        self._fullSizeImage: Optional[QWidget] = None

        # Keep track of whether the image is maximised or not
        self._imageMaximised = False

        # Set the window position and size
        self.setGeometry(300, 100, 1024, 768)

        # Set the default path
        self._currentPath = Path.home() / 'Pictures'

        # Set a time for 150ms to see if a file open event has happened, otherwise load the default folder
        QTimer.singleShot(150, self.StartUpTimerExpired)

        # Get the menubar
        self._menuBar = self.menuBar()

        # The image menu
        self._imageMenu: Optional[QMenu] = None

        # Create a Next acion to call _nextImage
        self._nextAction = QAction('Next', self)

        # Create a Previous acion to call _prevImage
        self._prevAction = QAction('Previous', self)

        # Add a menu for previous and next images, disabled to start with
        self._addImageMenu()

        # Show the window
        self.show()

    def _menuTest(self) -> None:
        print('Test')

    def _addImageMenu(self):
        # Create the Image menu
        self._imageMenu = self._menuBar.addMenu('Image')

        # Create a Next acion to call _nextImage
        self._nextAction.triggered.connect(self._nextImage) # type: ignore

        # Create a Previous acion to call _prevImage
        self._prevAction.triggered.connect(self._prevImage) # type: ignore

        # Add the actions to the Image Menu
        self._imageMenu.addAction(self._nextAction)
        self._imageMenu.addAction(self._prevAction)

        # Disable the actions for now
        self._nextAction.setEnabled(False)
        self._prevAction.setEnabled(False)

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

    def thumbnailClicked(self) -> None:
        # Get the widget that was clicked
        thumbnail = self.sender()

        # Get the widget is actually a thumbnail
        if isinstance(thumbnail, Thumbnail):
            # if this widget represents a folder, update the path and load the new set of thumbnails
            if thumbnail._imagePath.is_dir():
                # Update the path
                self._currentPath = thumbnail._imagePath

                # Clear and recreate the grid for this folder
                self.SetLabels()
            else:
                self.ShowImage(thumbnail._imagePath)

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

        # Add this widget to the stack
        self._stack.addWidget(self._fullSizeImage)

        # Swap the stack to this widget
        self._stack.setCurrentWidget(self._fullSizeImage)

        # Enable the previous and next image actions
        self._nextAction.setEnabled(True)
        self._prevAction.setEnabled(True)

        # Log that we are in maximaised image mode
        self._imageMaximised = True

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)

        if event.key() == Qt.Key.Key_Escape:
            # Close application on Escape
            self.close()
        elif self._imageMaximised:
            # If the image is maximised use the image key press handler
            self._ImageKeyEvent(event)
        else:
            # Otherwise use the file browser key press handler
            self._FileBrowserKeyEvent(event)

    def _FileBrowserKeyEvent(self, event: QKeyEvent) -> None:
        pass

    def _ImageKeyEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Up:
            # Reset the stack back to the scroll widget
            self._stack.setCurrentWidget(self._scroll)

            # Disable the previous and next image actions
            self._nextAction.setEnabled(False)
            self._prevAction.setEnabled(False)

            if self._fullSizeImage:
                # Remove the maximised image from the stack
                self._stack.removeWidget(self._fullSizeImage)

            # Indicate that the image is no longer maximised
            self._imageMaximised = False
        elif event.key() == Qt.Key.Key_Right:
            # Show the next image
            self._nextImage()
        elif event.key() == Qt.Key.Key_Left:
            # Show the previous image
            self._prevImage()

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
