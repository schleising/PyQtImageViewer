from dataclasses import dataclass
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

@dataclass
class FolderInfo:
    folderPath: Path
    highlightedItem: int
    scrollAmount: int

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

        # Create a graphics view with just the filename for now
        self._fullSizeImage = FullImage()

        # Add this widget to the stack
        self._stack.addWidget(self._fullSizeImage)

        # Keep track of whether the image is maximised or not
        self._imageMaximised = False

        # Set the window position and size
        self.setGeometry(START_X, START_Y, START_WIDTH, START_HEIGHT)

        # Set the minimum width
        self.setMinimumWidth(MIN_WIDTH)

        # Set the default path
        self._currentPath = Path.home() / 'Pictures'

        # Check this path exists, if not use home instead
        if not self._currentPath.exists():
            self._currentPath = Path.home()

        # Set a time for 150ms to see if a file open event has happened, otherwise load the default folder
        QTimer.singleShot(150, self.StartUpTimerExpired)

        # Add a menu for previous and next images, disabled to start with
        self._addMenu()

        # Store up which thumbnail is highlighted
        self._currentHighlightedThumbnail = 0

        # A dictionary containing the folder info for use if returning to that folder
        self._folderInfoDict: dict[Path, FolderInfo] = {}

        # Show the window
        self.show()

    def _addMenu(self):
        # Get the menubar
        self._menuBar = self.menuBar()

        # Create the menus
        self._fileMenu = self._menuBar.addMenu('File')
        self._viewMenu = self._menuBar.addMenu('Show')
        self._imageMenu = self._menuBar.addMenu('Image')

        # Add the actions to the file menu
        self._fileMenu.addAction('Save', QKeySequence.Save, self._fullSizeImage.SaveImage)

        # Add the actions to the view menu
        self._viewMenu.addAction('Return to Browser', QKeySequence(Qt.Key.Key_Up), self._returnToBrowser)
        self._viewMenu.addAction('Next', QKeySequence(Qt.Key.Key_Right), self._nextImage)
        self._viewMenu.addAction('Previous', QKeySequence(Qt.Key.Key_Left), self._prevImage)
        self._viewMenu.addSeparator()
        self._viewMenu.addAction('Zoom to Rect', QKeySequence(Qt.Modifier.META | Qt.Key.Key_Z), self._fullSizeImage.ZoomImage)
        self._viewMenu.addAction('Reset Zoom', QKeySequence(Qt.Modifier.META | Qt.Key.Key_R), self._fullSizeImage.ResetZoom)
        self._viewMenu.addSeparator()
        self._viewMenu.addAction('Image Information', QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_I), self._fullSizeImage.ImageInfo)

        # Add the actions to the image menu
        self._imageMenu.addAction('Crop to Rect', QKeySequence(Qt.Modifier.META | Qt.Key.Key_C), self._fullSizeImage.CropImage)
        self._imageMenu.addSeparator()
        self._imageMenu.addAction('Increase Colour', QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_Right), self._fullSizeImage.IncreaseColour)
        self._imageMenu.addAction('Decrease Colour', QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_Left), self._fullSizeImage.DecreaseColour)
        self._imageMenu.addAction('Increase Contrast', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_Right), self._fullSizeImage.IncreaseContrast)
        self._imageMenu.addAction('Decrease Contrast', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_Left), self._fullSizeImage.DecreaseContrast)
        self._imageMenu.addAction('Increase Brightness', QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Right), self._fullSizeImage.IncreaseBrightness)
        self._imageMenu.addAction('Decrease Brightness', QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Left), self._fullSizeImage.DecreaseBrightness)
        self._imageMenu.addAction('Black and White', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_W), self._fullSizeImage.BlackAndWhite)
        self._imageMenu.addSeparator()
        self._imageMenu.addAction('Sharpen', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_S), self._fullSizeImage.Sharpen)
        self._imageMenu.addAction('Blur', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_B), self._fullSizeImage.Blur)
        self._imageMenu.addAction('Contour', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_C), self._fullSizeImage.Contour)
        self._imageMenu.addAction('Detail', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_D), self._fullSizeImage.Detail)
        self._imageMenu.addAction('Edge Enhance', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_E), self._fullSizeImage.EdgeEnhance)
        self._imageMenu.addAction('Emboss', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_M), self._fullSizeImage.Emboss)
        self._imageMenu.addAction('Find Edges', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_F), self._fullSizeImage.FindEdges)
        self._imageMenu.addAction('Smooth', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_O), self._fullSizeImage.Smooth)
        self._imageMenu.addAction('Unsharp Mask', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_U), self._fullSizeImage.UnsharpMask)
        self._imageMenu.addAction('Auto Contrast', QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_A), self._fullSizeImage.AutoContrast)
        self._imageMenu.addSeparator()
        self._imageMenu.addAction('Undo', QKeySequence.Undo, self._fullSizeImage.UndoLastChange)

        # Disable the menus for now
        self._updateMenu()

    def _updateMenu(self) -> None:
        if self._imageMaximised:
            # Enable the menus
            self._fileMenu.setEnabled(True)
            self._viewMenu.setEnabled(True)
            self._imageMenu.setEnabled(True)
        else:
            # Disable the menus
            self._fileMenu.setEnabled(False)
            self._viewMenu.setEnabled(False)
            self._imageMenu.setEnabled(False)

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

            # Get the widget from the layout item
            widget = item.widget()

            # Check the widget is indeed a thumbnail
            if isinstance(widget, Thumbnail):
                # Cancel the image load
                widget.CancelLoad()

            # Set the parent to None to ensure it gets hidden
            widget.setParent(None) # type: ignore

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
            thumbnail = Thumbnail(imagePath, count)

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

        # Set the widow title to the folder name
        self.setWindowTitle(self._currentPath.stem)

        # Create a timer added to the end of the event queue to reset the scroll
        # bar and highlight the last thumbnail.  This cannot be done here as the 
        # view has not been painted and the thumbnail cannot yet be safely repainted
        # This fixes
        # 1) The view scroll position sometimes not being reset properly
        # 2) Occaisional crashes as we try to repaint a non-existent widget
        QTimer.singleShot(0, self.resetScroll)

    def thumbnailClicked(self) -> None:
        # Get the widget that was clicked
        thumbnail = self.sender()

        # Get the widget is actually a thumbnail
        if isinstance(thumbnail, Thumbnail):
            # Remove the current highlight
            self._thumbnailList[self._currentHighlightedThumbnail].highlighted = False
            
            # Get the item number to set the highlight
            self._currentHighlightedThumbnail = thumbnail.ItemNumber

            # Highlight the new thumbnail
            self._thumbnailList[self._currentHighlightedThumbnail].highlighted = True

            # if this widget represents a folder, update the path and load the new set of thumbnails
            self.OpenItem(thumbnail.ImagePath)

    def OpenItem(self, path: Path) -> None:
        if path.is_dir():
            # Save the current folder info
            folderInfo = FolderInfo(self._currentPath, self._currentHighlightedThumbnail, self._scroll.verticalScrollBar().value())
            self._folderInfoDict[self._currentPath] = folderInfo

            logging.log(logging.DEBUG, 'Saved Folder Info')
            logging.log(logging.DEBUG, self._currentPath)
            logging.log(logging.DEBUG, self._folderInfoDict[self._currentPath])
            logging.log(logging.DEBUG, '-----------------')

            # Update the path
            self._currentPath = path

            # Clear and recreate the grid for this folder
            self.SetLabels()
        else:
            # Show the image
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
        # View already created, it just needs reinitialisation with the new path
        self._fullSizeImage.InitialiseView(imagePath)

        # Swap the stack to this widget
        self._stack.setCurrentWidget(self._fullSizeImage)

        # Log that we are in maximaised image mode
        self._imageMaximised = True

        # Enable the previous and next image actions
        self._updateMenu()

        # Set the window title to folder - filename
        self.setWindowTitle(f'{self._currentPath.stem} - {imagePath.stem}')

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
                # Should never reach here, call the super class version of the function
                return super().eventFilter(watched, event)
        else:
            # We haven't dealt with the event so call the super class version of the function
            return super().eventFilter(watched, event)

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

        # Indicate that the image is no longer maximised
        self._imageMaximised = False

        # Disable the previous and next image actions
        self._updateMenu()

        # Set the window title back to the folder name
        self.setWindowTitle(self._currentPath.stem)

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

    def resetScroll(self) -> None:
        if self._currentPath in self._folderInfoDict:
            # Scroll the view back to where it was
            self._scroll.verticalScrollBar().setValue(self._folderInfoDict[self._currentPath].scrollAmount)

            # Highlight the old highlighted thumbnail
            self._currentHighlightedThumbnail = self._folderInfoDict[self._currentPath].highlightedItem

            logging.log(logging.DEBUG, 'Recovered Folder Info')
            logging.log(logging.DEBUG, self._currentPath)
            logging.log(logging.DEBUG, self._folderInfoDict[self._currentPath])
            logging.log(logging.DEBUG, f'Scroll Value: {self._scroll.verticalScrollBar().value()}')
            logging.log(logging.DEBUG, f'Scroll Limits: {self._scroll.verticalScrollBar().maximum()}')
            logging.log(logging.DEBUG, '-----------------')
        else:
            # Scroll the view to the top
            self._scroll.verticalScrollBar().setValue(0)

            # Highlight the first thumbnail
            self._currentHighlightedThumbnail = 0

        # Highlight the selected thumbnail        
        self._thumbnailList[self._currentHighlightedThumbnail].highlighted = True
