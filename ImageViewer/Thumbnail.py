from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtCore import Qt, pyqtSignal

from PIL import Image
from PIL.ImageQt import ImageQt

class Thumbnail(QWidget):
    # Class variables
    _initialised = False
    _defaultImagePath = 'ImageViewer/Resources/Loading Icon.png'
    _folderImagePath = 'ImageViewer/Resources/285658_blue_folder_icon.png'
    _defaultImage: Optional[QPixmap] = None
    _folderImage: Optional[ImageQt] = None
    _executor = ThreadPoolExecutor()
    _thumbnailSize = 0
    clicked = pyqtSignal()

    def __init__(self, imagePath: Path, parent: Optional[QWidget]=None):
        super().__init__(parent=parent)

        # Get labels for the image and filename and a layout to contain them
        self._thumbnailImage = QLabel()
        self._thumbnailText = QLabel()
        self._layout = QVBoxLayout()

        # Set the layout margins to 0 so they don't add to the grid margins
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Add the image and text labels to the layout
        self._layout.addWidget(self._thumbnailImage, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._layout.addWidget(self._thumbnailText, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Add the layout to this widget
        self.setLayout(self._layout)

        # Set the path of this image or folder
        self._imagePath = imagePath

        # Set the current image to None
        self._currentImage: Optional[QPixmap] = None

        # The actual image
        self._qtImage: Optional[ImageQt] = None
        
        # Set the default image, withe loading or a folder
        self.SetDefaultImage()

    @classmethod
    def InitialiseDefaultImage(cls, thumbnailSize: int) -> None:
        # Only do this is the class has not yet been initialised
        if not cls._initialised:
            # Set the thumbnail size of all thumbnails
            cls.UpdateThumbnailSize(thumbnailSize)

            # Read in the default image, using Pillow as it is quicker, and convert to a QPixmap
            pilImage = Image.open(cls._defaultImagePath)
            qtImage = ImageQt(pilImage)
            defaultPixmap = QPixmap()
            defaultPixmap.convertFromImage(qtImage)

            # Scale the pixmap to the thumbnail size
            cls._defaultImage = defaultPixmap.scaled(cls._thumbnailSize, cls._thumbnailSize, aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)

            # Read in the folder image, using Pillow as it is quicker, and convert to a QPixmap
            pilImage = Image.open(cls._folderImagePath)
            cls._folderImage = ImageQt(pilImage)

            # Show that the class is now initialised
            cls._initialised = True

    @classmethod
    def UpdateThumbnailSize(cls, thumbnailSize: int) -> None:
        # Set the thumbnail size
        cls._thumbnailSize = thumbnailSize

    def _ShortenLabelText(self, text: str) -> str:
        # Return a maximum of 15 characters for the filename (stem only)
        return text if len(text) <= 15 else f'{text[:6]}...{text[-6:]}'

    def SetDefaultImage(self) -> None:
        if self._imagePath.is_file():
            if self._defaultImage:
                # if this is a file, set the default loading image for now
                self._thumbnailImage.setPixmap(self._defaultImage)

                # Initiate the load of the actual image in another thread
                self._LoadImage()
        else:
            if self._folderImage:
                # if this is a folder, set the folder image
                folderPixmap = QPixmap()
                folderPixmap.convertFromImage(self._folderImage)

                # Scale the pixmap to the thumbnail size
                currentFolderImage = folderPixmap.scaled(self._thumbnailSize, self._thumbnailSize, aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
                self._thumbnailImage.setPixmap(currentFolderImage)
                self._currentImage = currentFolderImage

        # Set the filename text
        self._thumbnailText.setText(self._ShortenLabelText(self._imagePath.stem))

    def _LoadImage(self):
        # Load the image in a new thread
        self._executor.submit(self._LoadImageInThread)

    def _LoadImageInThread(self) -> None:
        # Use Pillow to open the image and convert to a QPixmap
        pilImage = Image.open(self._imagePath)
        self._qtImage = ImageQt(pilImage)

        # Resize the image
        self.ResizeImage()

    def ResizeImage(self) -> None:
        pixmap = QPixmap()

        # Check the Qt Image has been set
        if self._qtImage:
            # Convert the Qt Image into a QPixmap
            pixmap.convertFromImage(self._qtImage)
        elif self._folderImage:
            # Convert the Qt Image into a QPixmap
            pixmap.convertFromImage(self._folderImage)

        # Scale the image to the thumbnail size
        self._currentImage = pixmap.scaled(self._thumbnailSize, self._thumbnailSize, aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)

        if self._currentImage:
            # Set the image to be the label pixmap
            self._thumbnailImage.setPixmap(self._currentImage)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        super().mousePressEvent(a0)

        # Send the clicked message back to the main window
        self.clicked.emit()
