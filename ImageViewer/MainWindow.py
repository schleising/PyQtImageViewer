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

        # Set a time for 150ms to see if a file open event has happened, otherwise load the default folder
        QTimer.singleShot(150, self.StartUpTimerExpired)

        # Boolean to indicate whether we have already added the actions
        self._actionsAdded = False

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

        # Create a return to browser action to call _returnToBrowser
        self._returnAction = QAction('Return to Browser', self)
        self._returnAction.setShortcut(Qt.Key.Key_Up)

        # Create a return action to call _returnToBrowser
        self._returnAction.triggered.connect(self._returnToBrowser) # type: ignore

        # Create a Next action to call _nextImage
        self._nextAction = QAction('Next', self)
        self._nextAction.setShortcut(Qt.Key.Key_Right)

        # Create a Next action to call _nextImage
        self._nextAction.triggered.connect(self._nextImage) # type: ignore

        # Create a Previous action to call _prevImage
        self._prevAction = QAction('Previous', self)
        self._prevAction.setShortcut(Qt.Key.Key_Left)

        # Create a Previous action to call _prevImage
        self._prevAction.triggered.connect(self._prevImage) # type: ignore

        # Create the menus
        self._fileMenu = self._menuBar.addMenu('File')
        self._viewMenu = self._menuBar.addMenu('Show')
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

        # Add a Sharpen action
        self._sharpenAction = QAction('Sharpen', self)
        self._sharpenAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_S))

        # Add a Blur action
        self._blurAction = QAction('Blur', self)
        self._blurAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_B))

        # Add a Contour action
        self._contourAction = QAction('Contour', self)
        self._contourAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_C))

        # Add a Detail action
        self._detailAction = QAction('Detail', self)
        self._detailAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_D))

        # Add a Edge Enhance action
        self._edgeEnhanceAction = QAction('Edge Enhance', self)
        self._edgeEnhanceAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_E))

        # Add a Emboss action
        self._embossAction = QAction('Emboss', self)
        self._embossAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_M))

        # Add a Find Edges action
        self._findEdgesAction = QAction('Find Edges', self)
        self._findEdgesAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_F))

        # Add a Smooth action
        self._smoothAction = QAction('Smooth', self)
        self._smoothAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_O))

        # Add a Unsharp Mask action
        self._unsharpMaskAction = QAction('Unsharp Mask', self)
        self._unsharpMaskAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_U))

        # Add a Auto Contrast action
        self._autoContrastAction = QAction('Auto Contrast', self)
        self._autoContrastAction.setShortcut(QKeySequence(Qt.Modifier.ALT | Qt.Key.Key_A))

        # Add an Undo action
        self._undoAction = QAction('Undo', self)
        self._undoAction.setShortcut(QKeySequence.Undo)

        # Add a Save action
        self._saveAction = QAction('Save', self)
        self._saveAction.setShortcut(QKeySequence.Save)

        # Disable the actions for now
        self._updateMenu()

    def _updateMenu(self) -> None:
        # Only add the actions if they haven't already been added
        if not self._actionsAdded:
            # Connect to the zoom function of the full sized image
            self._zoomAction.triggered.connect(self._fullSizeImage.ZoomImage) # type: ignore

            # Connect to the reset zoom function of the full sized image
            self._resetZoomAction.triggered.connect(self._fullSizeImage.ResetZoom) # type: ignore

            # Connect to the crop function of the full sized image
            self._cropAction.triggered.connect(self._fullSizeImage.CropImage) # type: ignore

            # Connect to the crop function of the full sized image
            self._sharpenAction.triggered.connect(self._fullSizeImage.Sharpen) # type: ignore

            # Connect to the crop function of the full sized image
            self._blurAction.triggered.connect(self._fullSizeImage.Blur) # type: ignore

            # Connect to the crop function of the full sized image
            self._contourAction.triggered.connect(self._fullSizeImage.Contour) # type: ignore

            # Connect to the crop function of the full sized image
            self._detailAction.triggered.connect(self._fullSizeImage.Detail) # type: ignore

            # Connect to the crop function of the full sized image
            self._edgeEnhanceAction.triggered.connect(self._fullSizeImage.EdgeEnhance) # type: ignore

            # Connect to the crop function of the full sized image
            self._embossAction.triggered.connect(self._fullSizeImage.Emboss) # type: ignore

            # Connect to the crop function of the full sized image
            self._findEdgesAction.triggered.connect(self._fullSizeImage.FindEdges) # type: ignore

            # Connect to the crop function of the full sized image
            self._smoothAction.triggered.connect(self._fullSizeImage.Smooth) # type: ignore

            # Connect to the crop function of the full sized image
            self._unsharpMaskAction.triggered.connect(self._fullSizeImage.UnsharpMask) # type: ignore

            # Connect to the crop function of the full sized image
            self._autoContrastAction.triggered.connect(self._fullSizeImage.AutoContrast) # type: ignore

            # Connect to the undo function of the full sized image
            self._undoAction.triggered.connect(self._fullSizeImage.UndoLastChange) # type: ignore

            # Connect to the save function of the full sized image
            self._saveAction.triggered.connect(self._fullSizeImage.SaveImage) # type: ignore

            # Add the actions to the menus
            self._fileMenu.addAction(self._saveAction)

            self._viewMenu.addAction(self._returnAction)
            self._viewMenu.addAction(self._nextAction)
            self._viewMenu.addAction(self._prevAction)
            self._viewMenu.addSeparator()
            self._viewMenu.addAction(self._zoomAction)
            self._viewMenu.addAction(self._resetZoomAction)

            self._imageMenu.addAction(self._cropAction)
            self._imageMenu.addSeparator()
            self._imageMenu.addAction(self._sharpenAction)
            self._imageMenu.addAction(self._blurAction)
            self._imageMenu.addAction(self._contourAction)
            self._imageMenu.addAction(self._detailAction)
            self._imageMenu.addAction(self._edgeEnhanceAction)
            self._imageMenu.addAction(self._embossAction)
            self._imageMenu.addAction(self._findEdgesAction)
            self._imageMenu.addAction(self._smoothAction)
            self._imageMenu.addAction(self._unsharpMaskAction)
            self._imageMenu.addAction(self._autoContrastAction)
            self._imageMenu.addSeparator()            
            self._imageMenu.addAction(self._undoAction)

            # Indicate that the actions have been added
            self._actionsAdded = True

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
