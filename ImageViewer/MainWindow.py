
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QScrollArea, QGridLayout, QWidget, QLabel, QStackedWidget
from PyQt6.QtGui import QAction, QKeyEvent
from PyQt6.QtCore import Qt

from ImageViewer.Thumbnail import Thumbnail
from ImageViewer.FileTypes import supportedExtensions

class MainWindow(QMainWindow):
    """Main Window."""
    def __init__(self, label: str, parent:Optional[QWidget]=None):
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

        # Create a menu (this doesn't seem to actually work just yet)
        self._createMenu()

        # Set the numner of thumbnails per row to 8
        self._thumbnailsPerRow = 8

        # Create a thumbnail list
        self._thumbnailList: list[Thumbnail] = []

        # Set the default path
        self._defaultPath = Path.home() / 'Pictures'

        # Setup a label for the full sized image
        self._fullSizeImage: Optional[QLabel] = None

        # Keep track of whether the image is maximised or not
        self._imageMaximised = False

    def _createMenu(self):
        self.menu = self.menuBar()
        closeAction = QAction('&Exit', self)
        closeAction.triggered.connect(self.close) # type: ignore
        self.fileMenu = self.menuBar().addMenu('File')
        self.fileMenu.addAction(closeAction)
        self.setMenuBar(self.menu)

    def _GetImagePathList(self, imagePath: Path) -> list[Path]:
        # Return the list of images Paths, sorted alphabetically (case insensitive)
        return sorted([image for image in imagePath.iterdir() if image.suffix.lower() in supportedExtensions.values()], key=lambda x: x.name.lower())

    def _GetFolderList(self, imagePath: Path) -> list[Path]:
        # Get the list of non-hidden folders in this folder
        folderList = sorted([path for path in imagePath.iterdir() if path.is_dir() and not path.name.startswith('.')], key=lambda x: x.name.lower())

        # Insert the parent folder at the front of the list
        folderList.insert(0, imagePath.parent)

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
        self._imageList = self._GetFolderList(self._defaultPath)

        # Get the list of images in this folder and extend the folder list
        self._imageList.extend(self._GetImagePathList(self._defaultPath))

        # Calculate the thumbnail size
        thumbnailSize = (self.width() // self._thumbnailsPerRow) - 2 * self._grid.getContentsMargins()[0]

        # Initialise the default image (this should only actually happen once)
        Thumbnail.InitialiseDefaultImage(thumbnailSize)

        # Loop through the folders and images, creating a thumbnail for each
        for count, imagePath in enumerate(self._imageList):
            # Create the thumbnail, will only have the default or folder image for now
            thumbnail = Thumbnail(imagePath)

            #Work out the grid x and y position
            startX = count // self._thumbnailsPerRow
            startY = count % self._thumbnailsPerRow

            # Add the thumbnail widget to the grid, aligning centrally
            self._grid.addWidget(thumbnail, startX, startY, alignment=Qt.AlignmentFlag.AlignCenter)

            # Append this to the list of thumbnails
            self._thumbnailList.append(thumbnail)

            # Connect the click on a thumbnail to this window
            thumbnail.clicked.connect(self.thumbnailClicked)

    def thumbnailClicked(self) -> None:
        # Get the widget that was clicked
        thumbnail = self.sender()

        # Get the widget is actually a thumbnail
        if isinstance(thumbnail, Thumbnail):
            # if this widget represents a folder, update the path and load the new set of thumbnails
            if thumbnail._imagePath.is_dir():
                # Update the path
                self._defaultPath = thumbnail._imagePath

                # Clear and recreate the grid for this folder
                self.SetLabels()
            else:
                # Create a label with just the filename for now
                self._fullSizeImage = QLabel(f'{thumbnail._imagePath.name}')

                # Add this widget to the stack
                self._stack.addWidget(self._fullSizeImage)

                # Swap the stack to this widget
                self._stack.setCurrentWidget(self._fullSizeImage)

                # Log that we are in maximaised image mode
                self._imageMaximised = True

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)

        # Check for the user pressing escape
        if event.key() == Qt.Key.Key_Escape:
            # If the image is maximised
            if self._imageMaximised:
                # Reset the stack back to the scroll widget
                self._stack.setCurrentWidget(self._scroll)
                if self._fullSizeImage:
                    # Remove the maximised image from the stack
                    self._stack.removeWidget(self._fullSizeImage)

                # Indocate that the image is no longer maximised
                self._imageMaximised = False
            else:
                # If in file browser mode close the application
                self.close()
